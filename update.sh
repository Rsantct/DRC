#!/bin/bash

cd ~/

mkdir -p ~/DRC

rm -f ~/master.zip*

wget https://github.com/Rsantct/DRC/archive/master.zip
unzip -o master.zip

rm -rf ~/DRC
mv ~/DRC-master ~/DRC
rm ./update.sh

chmod -R +x ~/DRC/*py
chmod -R +x ~/DRC/*sh
