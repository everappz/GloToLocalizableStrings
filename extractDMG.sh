#!/bin/sh

usage() {
   echo "$0 /path/to/image.dmg [/output/path]"
   exit 0
}

DMG=$1
OUTPUT=$2

[ "x$DMG" != "x" ] || usage
[ "x$OUTPUT" != "x" ] || OUTPUT="."
[ -f $DMG ] || usage
[ -d $OUTPUT ] || OUTPUT="."

echo Extract $DMG to $OUTPUT

MOUNTINFO=$(hdiutil attach $DMG)
MOUNTDISK=$(echo $MOUNTINFO | awk '{print $1}')
MOUNTDISK_ESCAPED=$(echo $MOUNTDISK | sed -e 's/\//\\\//g')
MOUNTPOINT=$(echo $MOUNTINFO | sed -e "s/$MOUNTDISK_ESCAPED//" | sed -e 's/^[^\/]*//')
cp -r $MOUNTPOINT/* $OUTPUT
hdiutil detach $MOUNTDISK
