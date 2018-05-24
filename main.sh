#!/bin/sh

CURRENTPATH=`pwd`
#ARCHS="ios macos tvos watchos"
ARCHS="ios"

for ARCH in ${ARCHS}
do

BUILD_DIR="${CURRENTPATH}/build/${ARCH}"
RESULT_DIR="${CURRENTPATH}/res/${ARCH}"

rm -rf $RESULT_DIR
mkdir -p $RESULT_DIR

echo "BUILDING FOR ${ARCH}"

FILES="${CURRENTPATH}/${ARCH}/*.dmg"

for FILE in $FILES
do
echo $FILE
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR
FILENAME=$(basename -- "$FILE")
STRINGS_FILE="${RESULT_DIR}/${FILENAME%.*}.strings"
rm -rf $STRINGS_FILE
echo '' > $STRINGS_FILE
sh ./extractDMG.sh $FILE $BUILD_DIR
python strings.py $STRINGS_FILE $BUILD_DIR
done

done

