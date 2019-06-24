#!/usr/bin/env bash

IFS=':'
for path in $PYTHONPATH; do
    file=`find $path -name ordt_addrmap.py -print -quit`
    case $file in
	'') ;;
	*) sed '/\/usr\/bin\/env/ r LICENSE' $file  > ./ordt_addrmap.py ; break ;;
    esac
done
