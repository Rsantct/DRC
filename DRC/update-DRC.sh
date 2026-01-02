#!/bin/bash

function print_help {
    echo
    echo "  Usage:   update-DRC.sh [branch]"
    echo
    echo "           default branch is 'master'"
    echo
}

ocp=$1

if [[ $1 ==  *"-h"* ]]; then
    print_help
    exit 0
fi

branch="master"
if [[ $1 ]]; then
    branch=$1
fi

gituser="Rsantct"
if [[ $2 ]]; then
    gituser=$2
fi
gitsite="https://github.com/""$gituser"

print_help
echo
echo "    (i) Will download from: ""$gitsite""/""$branch"
echo
read -r -p "    Is that OK? [y/N] " tmp
if [ "$tmp" != "y" ] && [ "$tmp" != "Y" ]; then
    echo 'Bye.'
    exit 0
fi

mkdir -p ~/Downloads

cd ~/Downloads

rm -f "$branch".zip 1>/dev/null 2>&1

curl -LO "$gitsite"/DRC/archive/"$branch".zip

unzip -o "$branch".zip

rm -f "$branch".zip 1>/dev/null 2>&1

# delete only files, keep user directories under DRC if any
echo "Removing old files under ~/DRC"
find ~/DRC -maxdepth 1 -type f -delete

cp -r ./DRC-"$branch"/DRC    ~/
cp    ./DRC-"$branch"/bin/*  ~/bin/
chmod +x ~/DRC/*.py
chmod +x ~/DRC/*.sh
chmod +x ~/bin/DRC*

# Leaving a dummy file with the installes branch name
touch ~/DRC/"$branch"_FROM_"$gituser"
echo
echo installed under:  "$HOME"/DRC
echo

cd
