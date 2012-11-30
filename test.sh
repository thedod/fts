#!/bin/sh -e

export PATH=$PATH:$(pwd)

tmpf=$(mktemp -t $(basename $0).$$)
trap "rm -f $tmpf" EXIT

# just make sure it runs
fts --help

echo creating data
./rando.sh | sed 's/^/    /'

echo deleting old data
rm -f .fts.db

echo creating initial db
fts --init --ignore-re '/fts$'

search=$(cat $(ls rando/* | unsort | head -n 1) | unsort | head -n 1)
echo test search "($search)"
fts "$search"

echo more data
./rando.sh | sed 's/^/    /'

echo test sync
fts --sync

echo more data
./rando.sh | sed 's/^/    /'
pushd rando > /dev/null

    echo sync from in rando
    fts --sync
    search=$(cat $(ls | unsort | head -n 1) | unsort | head -n 1)
    echo search from in rando "($search)"
    fts "$search" | tee $tmpf

    ignorefile=$(cat $tmpf | head -n 1)

    echo ignoring $ignorefile for search $search
    fts --ignore-simple $ignorefile
    fts --sync

    if fts "$search" | grep $(cat $tmpf | head -n 1); then
        echo "Shouldn't have been able to find $ignorefile in $search"
        exit 1
    fi

popd > /dev/null

