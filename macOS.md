
## Install on Mac OS

### Python3

Go to http://www.python.org.

Download the current python3 package then install it as usual.

Open a terminal and run python3 for first time:

    python3

Maybe you will be requiered to **install Apple's _'command line toools'_**

--> ACCEPT ( this will take a while...) <--

Exiting from the python interpreter:

    rafael@mbp ~ % python3
    Python 3.9.0 (v3.9.0:9cf6752276, Oct  5 2020, 11:29:23) 
    [Clang 6.0 (clang-600.0.57)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    >>> exit()
    rafael@mbp ~ % 


### Standard Python modules:

- pip: the standard Python packages manager.
- numpy, scipy, matplotlib: scientific modules.
- sounddevice: universal sound interfacing based on PortAudio.
- pyaml: an standard parser.

Open a terminal and run:

    sudo pip3 install --upgrade pip
    sudo pip3 install --upgrade setuptools
    sudo pip3 install numpy matplotlib scipy sounddevice pyaml

### AudioHumLab/audiotools

Open a terminal and run:

    curl -O  https://raw.githubusercontent.com/Rsantct/audiotools/master/update-audiotools.sh
    sh update-audiotools.sh master

        (i) Will download from: [ https://github.com/AudioHumLab ]
            Is this OK? [y/N]  Y
             
### Optional desktop shortcut

After installig DRC on your Mac as described in then main **README.md**, you can have a desktop shortcut for the DRC_GUI app.

Open a terminal and run:

    osascript -e 'tell application "Finder" to make alias file to POSIX file "'$HOME'/DRC/DRC_GUI.py" at POSIX file "'$HOME'/Desktop"'
    mv $HOME/Desktop/DRC_GUI.py $HOME/Desktop/DRC_GUI


