#!/bin/bash

# Numera los drc-X... con el número indicado para los _lp_
# y uno más para los _mp_


if [[ $1 ]]; then
    n1=$1
    n2=$(( n1+1 ))
    for x in drc*; do
        if [[ "$x" == *"_lp_"* ]];then
            mv $x ${x/X/$n1}
        else
            mv $x ${x/X/$n2}
        fi
    done
else
    echo "indicar el numero que debe sustiruir a drc-X-......"
fi

