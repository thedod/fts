import os
import os.path
import errno
import stat
import time
from functools import partial

from ftsdb import update_document, add_document, prefix_expr, logger, Cursor

def visitor(path, prefix, simple_exclusions, cu, dirname, fnames):
    if simple_exclusions:
        simple_removes = set(fnames).intersection(simple_exclusions)
        for sr in simple_removes:
            fnames.remove(sr)

    for sname in fnames:
        fname = os.path.join(dirname, sname)

        assert fname.startswith(path)
        if prefix:
            assert fname.startswith(os.path.join(path, prefix))

        dbfname = fname[len(path)+1:]

        st = os.stat(fname)
        mode = st.st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            logger.warn("Skipping non-regular file %s (%s)", dbfname, stat.S_IFMT(mode))
            continue

        cu.execute("INSERT INTO ondisk(path, dbpath, last_modified) VALUES (?, ?, ?)",
                   (fname, dbfname, int(st[stat.ST_MTIME])))

def sync(conn, path, prefix, files = None):
    # path must be a full path on disk
    # prefix must be the full path on disk that we're syncing (or empty)

    start = time.time()

    news = updates = deletes = 0

    with Cursor(conn) as c, Cursor(conn) as cu:
        c.execute("""
                  CREATE TEMPORARY TABLE
                  ondisk (
                     path          TEXT PRIMARY KEY COLLATE BINARY,
                     dbpath        TEXT COLLATE BINARY,
                     last_modified INTEGER
                  );
                  """)

        c.execute("SELECT expression FROM exclusions WHERE type = 'simple'")
        simple_exclusions = set(x[0] for x in c.fetchall())

        wpath = path
        if prefix:
            wpath = os.path.join(path, prefix)

        if files is None:
            os.path.walk(wpath, partial(visitor, path, prefix, simple_exclusions), cu)
        else:
            visitor(path, prefix, simple_exclusions, cu, wpath, files)

        # remove anyone that matches our ignore globs
        cu.execute("""
            DELETE FROM ondisk WHERE path in
            (SELECT od.path
               FROM ondisk od, exclusions e
              WHERE (e.type = 'glob'   AND od.path GLOB   e.expression)
                 OR (e.type = 're'     AND od.path REGEXP e.expression)
                 OR (e.type = 'simple' AND IGNORE_SIMPLE(od.path, e.expression)
            )
        )""")
        ignores = cu.rowcount

        # now build three groups: new files to be added, missing files to be
        # deleted, and old files to be updated

        # updated ones
        c.execute("""
            SELECT f.docid, od.path, od.last_modified
              FROM ondisk od, files f
             WHERE od.dbpath = f.path
               AND f.last_modified < od.last_modified
        """)
        for (docid, path, last_modified) in c:
            logger.debug("Updating %r", path)
            try:
                update_document(cu, docid, last_modified, open(path).read())
            except IOError as e:
                if e.errno in (errno.ENOENT, errno.EPERM):
                    logging.warning("Skipping %s: %s", path, os.strerror(e.errno))
                else:
                    raise
                continue
            updates += 1

        if files is None:
            # ones to delete
            c.execute("""
                      CREATE TEMPORARY TABLE deletedocs (
                          docid integer primary KEY
                      );
            """)
            c.execute("""
                      INSERT INTO deletedocs(docid)
                      SELECT f.docid
                        FROM files f
                       WHERE (? = '' OR f.path LIKE ? ESCAPE '\\')
                         AND f.path NOT IN (SELECT dbpath FROM ondisk od)
            """, (prefix, prefix_expr(prefix),))
            c.execute("""
                DELETE FROM files WHERE docid IN (SELECT docid FROM deletedocs);
            """)
            c.execute("""
                DELETE FROM files_fts WHERE docid IN (SELECT docid FROM deletedocs);
            """)
            deletes = c.execute("SELECT COUNT(*) FROM deletedocs").fetchone()[0]
            c.execute("""
                DROP TABLE deletedocs;
            """)

        # new files to create
        c.execute("""
             SELECT od.path, od.dbpath, od.last_modified
               FROM ondisk od
              WHERE od.dbpath NOT IN (SELECT path FROM files)
        """)
        for (fname, dbpath, last_modified) in c:
            # is it safe to re-use the last_modified that we got before, or
            # do we need to re-stat() the file?
            logger.debug("Adding new file %r", fname)
            try:
                add_document(cu, dbpath, last_modified, open(fname).read())
            except IOError as e:
                if e.errno in (errno.ENOENT, errno.EPERM):
                    logging.warning("Skipping %s: %s", fname, os.strerror(e.errno))
                else:
                    raise
                continue
            news += 1

        logger.info("%d new documents, %d deletes, %d updates, %d ignored in %.2fs", news, deletes, updates, ignores, time.time()-start)
