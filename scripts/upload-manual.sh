#!/bin/sh
#
# This script puts the manual into a zip file for uploading to
# pythonhosted.org. Then it gives instructions on how to upload the
# archive.
# 


DIR=$(mktemp -d --tmpdir pyinstaller-doc.XXXXXX)
FILE=$(mktemp --tmpdir pyinstaller-doc-XXXXXX.zip)

cd doc
mkdir -p "$DIR"
cp -ar Manual.html "$DIR"/index.html
cp -ar images stylesheets "$DIR"

cd "$DIR"

# Using python since `zip`'s command-line-usage is  mess
python -m zipfile -c "$FILE" *
python -m zipfile -l "$FILE"

rm -rf "$DIR"

echo
echo 'Now go to https://pypi.python.org/pypi?%3Aaction=pkg_edit&name=PyInstaller'
echo 'and upload file' "$FILE"
