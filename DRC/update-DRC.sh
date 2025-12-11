#!/bin/sh

if [ -z $1 ] ; then
    echo
    echo "  Usage:"
    echo
    echo "      update-DRC.sh [branch]"
    echo
    echo "      normal branch is 'master'"
    echo
    exit 0
fi
branch=$1


gituser="Rsantct"
if [ $2 ]; then
    gituser=$2
fi
gitsite="https://github.com/""$gituser"


echo
echo "(i) Will download from: ""$gitsite""/""$branch"
echo
read -r -p "    Is this OK? [y/N] " tmp
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

rm -rf ~/DRC  1>/dev/null 2>&1

cp -r ./DRC-"$branch"/DRC    ~/
cp    ./DRC-"$branch"/bin/*  ~/bin/
chmod +x ~/DRC/*.py
chmod +x ~/DRC/*.sh
chmod +x ~/bin/DRC*

# Leaving a dummy file with the installes branch name
touch ~/DRC/"$branch"_BRANCH_FROM_"$gituser"
echo
echo installed under:  "$HOME"/DRC
echo

cd
