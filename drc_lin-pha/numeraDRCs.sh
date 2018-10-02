#!/bin/bash

if [[ $1 ]]; then
    for x in drc*; do
        mv $x ${x/X/$1}
    done
else
    echo "indicar el numero que debe sustiruir a drc-X-......"
fi

