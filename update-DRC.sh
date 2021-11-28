#!/bin/sh

# (i) NOTICE:   When maintaining this script, do NOT edit it directly
#               from ~/DRC because it will be modified on runtime.
#               So edit it apart, copy to ~/DRC and test it.

if [ -z $1 ] ; then
    echo "usage:"
    echo "    update-DRC.sh   master   [git_repo]"
    echo
    echo "    (i) Default git_repo:                     'AudioHumLab'"
    echo "        You can use another branch name than  'master' "
    echo
    exit 0
fi
branch=$1

reponame="AudioHumLab"
if [ $2 ]; then
    reponame=$2
fi
gitsite="https://github.com/""$reponame"


echo
echo "(i) Will download from: [ ""$gitsite"" ]"
read -r -p "    Is this OK? [y/N] " tmp
if [ "$tmp" != "y" ] && [ "$tmp" != "Y" ]; then
    echo 'Bye.'
    exit 0
fi

cd ~/

# Remove previous
rm -f ~/$branch.zip*    1>/dev/null 2>&1

# Download project from GitHUb
curl -LO "$gitsite"/DRC/archive/$branch.zip
# Unzip ( ~/DRC-$branch/... )
unzip -o $branch.zip

# Remove old
rm -rf ~/DRC     1>/dev/null 2>&1

# Rename folder
mv ~/DRC-$branch ~/DRC

# Executable flags
chmod +x ~/DRC/*.py
chmod +x ~/DRC/*.sh

# Leaving a dummy file with the installes branch name
touch ~/DRC/"$branch"_FROM_"$reponame"

# Removing <branch>.zip
cd ~/
rm -f ~/$branch.zip         1>/dev/null 2>&1
rm ~/update-DRC.sh          1>/dev/null 2>&1

echo
echo installed under:  "$HOME"/DRC
echo

# Updating <branch> on GUI window title

sed -i.bak -e \
    s/self.title\(\'AudioHumLab\\/DRC\'\)/self.title\(\'$reponame\\/DRC\'\)/g  \
    DRC/DRC_GUI.py

rm DRC/DRC_GUI.py.bak
