#!/bin/bash

# Des-numera:
#    drc-X-L_des_crip_cion.pcm  --->  drc.L_des_crip_cion.pcm

for x in drc*; do
    if [[ true  ]]; then
        newname=${x/-?-/.}
        echo $x'   ---->  '$newname
        mv "$x" "$newname"
    fi
done

