# Copy this file to webconfig.py and edit it. It only contains
# the variable "folders": a dict that maps logical names
# passed as the "f" url arg (e.g. ?f=mybook&q=nevermore)
# to folders where you have text (not html), and a .fts.db
# (i.e. fts --init was run there)
# You can use https://github.com/aaronsw/html2text to convert.
# Create a text/ folder where html/ is, and do:
#   for f in html/*htm ; do
#       html2text.py  "$f" utf-8 > "text/$(basename "$f" htm)txt"
#   done
# Then create the fts db there:
#   cd text
#   fts --init
# Then add that folder here.
# If you change the html, rerun htmltext.py loop and then:
#   cd /PATH/TO/text
#   fts --sync

folders = {
 "mybook":"/PATH/TO/MYBOOK",
 "otherbook":"/PATH/TO/OTHERBOOK",
}
