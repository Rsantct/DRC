
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


### Update standard Python modules:

    sudo pip3 install --upgrade pip
    sudo pip3 install --upgrade setuptools
    sudo pip3 install numpy matplotlib scipy sounddevice pyaml

### Download and install AudioHumLab/audiotools

    curl -O  https://raw.githubusercontent.com/Rsantct/audiotools/master/update-audiotools.sh
    sh update-audiotools.sh master

        (i) Will download from: [ https://github.com/AudioHumLab ]
            Is this OK? [y/N]  Y
             
             
### Download and install AudioHumLab/DRC

    curl -O  https://raw.githubusercontent.com/Rsantct/DRC/master/update-DRC.sh
    sh update-DRC.sh master

        (i) Will download from: [ https://github.com/AudioHumLab ]
            Is this OK? [y/N]  Y


You are done, you can run the DRC graphic user interface:

    ~/DRC/DRC_GUI.py &


### Update

    ~/DRC/update-DRC.sh master

    ~/audiotools/update-audiotools.sh master

