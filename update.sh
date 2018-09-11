#!/bin/bash

cd ~/

rm -f ~/master.zip*

wget https://github.com/Rsantct/DRC/archive/$branch.zip
unzip -o master.zip

rm -rf ~/DRC
mv ~/DRC-master ~/DRC

chmod -R +x ~/DRC/*py
chmod -R +x ~/DRC/*sh
