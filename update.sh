#!/bin/sh

branch="master"
if [ $1 ]; then
  branch=$1
else
  echo 'update.sh   master | alternative_branch'
  exit 0
fi

cd ~/

mkdir -p ~/DRC

rm -f ~/"$branch".zip*

wget https://github.com/Rsantct/DRC/archive/"$branch".zip
unzip -o "$branch".zip
rm -f ~/"$branch".zip*

rm -rf ~/DRC
mv ~/DRC-"$branch" ~/DRC

chmod +x ~/DRC/*.py

rm ./update.sh  > /dev/null 2>&1
