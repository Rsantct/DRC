#!/bin/bash

branch="master"
if [[ $1 ]]; then
  branch=$1
fi

cd ~/

mkdir -p ~/DRC

rm -f ~/"$branch".zip*

wget https://github.com/Rsantct/DRC/archive/"$branch".zip
unzip -o "$branch".zip
rm -f ~/"$branch".zip*

rm -rf ~/DRC
mv ~/DRC-"$branch" ~/DRC

chmod +x ~/DRC/drc_multipoint/*.py
chmod +x ~/DRC/drc_multipoint/*.sh
chmod +x ~/DRC/logsweep2TF/*.py

rm ./update.sh  > /dev/null 2>&1
