#!/bin/bash

# Des-numera los drc-X...

for x in drc*; do
    if [[ true  ]]; then
        newname=${x/-?-/.}
        echo $x'   ---->  '$newname
        mv "$x" "$newname"
    fi
done

