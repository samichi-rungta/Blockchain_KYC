#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <file>"
    exit 1
fi

FILE=$1
HASH=$(sha256sum $FILE | awk '{ print $1 }')

echo $HASH

