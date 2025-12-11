
# Install on Mac OS

## Python

### Homebrew

This is the preferred way to go

    brew install python
    brew install python-tk  # the standard GUI library

### Python.org

_Deprecated, please use Homebrew as above_

Go to http://www.python.org. Download the current python3 package then install it as usual.

Open a terminal and run python3 for first time:

    python3

Maybe you will be requiered to **install Apple's _command line toools_**, this will take a while ...

## Python modules

DRC needs some additional modules to work.

- numpy, scipy, matplotlib: scientific modules.
- sounddevice: universal sound interfacing based on PortAudio.
- pyaml: a standard parser.
- Pillow: python imaging library

In most recent Python versions, these must be installed under a _Python Virtual Environment_, that is, not globally.

    $ python3 -m venv --system-site-packages ~/.env
    $ source ~/.env/bin/activate
    (.env) $
    (.env) $ pip3 install Pillow numpy matplotlib scipy sounddevice pyaml

Deactivate is NOT necessary

    (.env) $ deactivate
    $


## Rsantct/audiotools

Open a terminal and run:

    curl -O  https://raw.githubusercontent.com/Rsantct/audiotools/master/update-audiotools.sh

    sh update-audiotools.sh master

        (i) Will download from: [ https://github.com/Rsantct ]
            Is this OK? [y/N]  Y


## Optional desktop shortcut

After installig DRC on your Mac as described in then main **README.md**, you can have a desktop shortcut for the DRC_GUI app.

Please follow the below steps:


- Configure Apple's 'Python Launcher'

    - Finder > Applications > Python 3.x > Python Launcher

        - Settings for file type:  Python Script

        - Interpreter: /usr/local/bin/python3

        - [x] Run in a Terminal window



- Configure **DRC_GUI.py** to be open whit Apple's 'Python Launcher':

    - In Finder, go to your DRC folder, right click on the DRC_GUI.py file, then choose 'Get information' (CMD + I)

        --> Open with: 'Python Launcher'



- Make the desktop shortcut, by open a terminal and running:

    ```
    osascript -e 'tell application "Finder" to make alias file to POSIX file "'$HOME'/DRC/DRC_GUI.py" at POSIX file "'$HOME'/Desktop"'

    mv $HOME/Desktop/DRC_GUI.py $HOME/Desktop/DRC_GUI
    ```





