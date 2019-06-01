#!/bin/bash

read -p 'Range begin: ' rangeBegin
read -p 'Range end: ' rangeEnd
read -p 'Certificate file: ' fileCert
read -p 'Private key file: ' fileKey

echo
echo Range: $rangeBegin - $rangeEnd
echo Certificate file: $fileCert
echo Private key gile: $fileKey

for ((x=$rangeBegin; x<=$rangeEnd; x++ ));
do
    wget --no-parent --certificate=$fileCert --private-key=$fileKey -r -np https://www.monroe-system.eu/user/$x/
done
