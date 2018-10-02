#!/bin/bash

if [[ $1 ]]; then
    for x in drc*; do
        mv $x ${x/room_avg/$1}
    done
else
    echo "indicar el texto que debe sustituir a 'room_avg'"
fi

