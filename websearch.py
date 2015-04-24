#!/usr/bin/env python2.7
import web,json
# allow symlinking to this as a cgi
import os,sys
sys.path.insert(0,os.path.dirname(os.path.realpath(__file__)))

from ftsdb import finddb

from ftssearch import search,snippet_color,snippet_end_color,snippet_elipsis

### see webconfig-example.py
from webconfig import folders

### utilities

def ansi2html(s):
   return s.replace(snippet_elipsis,''
       ).replace(snippet_color,'<strong>'
       ).replace(snippet_elipsis,''
       ).replace(snippet_end_color,'</strong>')

### Web server

urls = (
    '/', 'Root',
)
    
class Root:
    def GET(self):
        form = web.input(q='',f='')
        web.header('Content-type','application/json')
        if not form.q:
            return json.dumps({"status":"fail","error":"bad or missing query"})
        folder = folders.get(form.f)
        if not folder:
            return json.dumps({"status":"fail","error":"bad or missing folder"})
        root, prefix, conn = finddb(folder)
        matches = []
        with conn:
            for sr in search(conn, prefix, form.q, 'MATCH', False, True):
                matches.append( {"id":sr.filename.rsplit('.',1)[0],"match":ansi2html(sr.snippet)} )
        return json.dumps({"status":"success","q":form.q,"matches":matches},indent=form.get('pretty') and 4 or None)

if __name__ == "__main__":
    #web.config.debug = True
    app = web.application(urls, globals()) 
    app.run()
