#!/bin/bash

cd ~/

mkdir -p ~/DRC

rm -f ~/master.zip*

wget https://github.com/Rsantct/DRC/archive/master.zip
unzip -o master.zip

rm -rf ~/DRC
mv ~/DRC-master ~/DRC

chmod +x ~/DRC/drc_lin-pha/*py
chmod +x ~/DRC/logsweep2TF/*py
chmod +x ~/DRC/swept_sine/*py

rm ./update.sh

