This soft is intended to measure a loudspeaker's in-room response, then calculate FIR filter to perform DRC equalization (digital room correction). You'll ned to use a convolver inserted in the loudspeakers signal path, such as Brutefir as used [here](https://github.com/AudioHumLab/pe.audio.sys)


## Multipoint measurement

The main meas script is **`logsweep2TF.py`**. It is based on a public lisenced Matlab program from Richard Mann y John Vanderkooy, published at [linearaudio.net](https://linearaudio.net/downloads) (Vol.13).

The script **`roommeasure.py`** allows to perform **_stationary measurements in several mic locations_**, then resulting an averaged frequency response in .frd file format.

The spatial amplitude for mic locations relies in the user criteria, depending on the listening scenario.


### JACK management

When measuring a [JACK based loudspeaker system](https://github.com/AudioHumLab), **`roommeasure.py`** can help on routing the loudspeaker system stereo soundcard analog input towards the convenient loudspeaker channel. So you won't need to rewire your cable from L to R and so on ;-)

## GUI appearance:

![GUI](https://github.com/Rsantct/DRC/blob/master/doc/roommeasure_GUI_screen_1.png)


Testing the log-sweep recording:

![GUI](https://github.com/Rsantct/DRC/blob/master/doc/test_sweep.png)


## DRC EQ filter calculation

The script **`roomEQ.py`** is in charge to calculate the FIR filter for DRC EQ, from a given `.frd` freq response file, as the one provided from **`roommeasure.py`**, or other software e.g : ARTA or Room EQ Wizard.

**`roomEQ.py`** allows to generate FIR with variable length (resolution) and/or sampling frequency.

The **reference level** on which it is applied the EQ is automatically detected, but you can manually choose it after visualizing the proposed curves.


```
~$ roomEQ.py 

    roomEQ.py

    Calculates a room equalizer FIR from a given in-room response, usually an
    averaged one as the provided from 'roommeasure.py'.

    Usage:

        roomEQ.py response.frd  [ options ]

            -fs=    Output FIR sampling freq (default 48000 Hz)

            -e=     Exponent 2^XX for FIR length in taps.
                    (default 15, i.e. 2^15=32 Ktaps)

            -ref=   Reference level in dB (default autodetected)

            -scho=  Schroeder freq. (default 200 Hz)

            -wFc=   Gaussian window to limit positive EQ: center freq
                    (default 1000 Hz)

            -wOct=  Gaussian window to limit positive EQ: wide in octaves
                    (default 10 octaves 20 ~ 20 KHz)

            -noPos  Does not allow positive gains at all

            -doFIR  Generates the pcm FIR after estimating the final EQ.

            -plot   FIR visualizer

            -dev    Auxiliary plots

```

![gaps](https://github.com/Rsantct/DRC/blob/master/doc/roomEQ_hard-modes.png)



## FIR application

The obtained FIR filter, must be loaded in a convolver as Brutefir in Linux, or in a generic reverb plugin as Wave's IR1 in a DAW, or in a hardware convolver as miniDSP.

Here we propose the evolutions [pe.audio.sys](https://github.com/AudioHumLab) or [pre.di.c](https://github.com/AudioHumLab) fron the original project [FIRtro](https://github.com/AudioHumLab/FIRtro/wiki/01---Introducción) (currently not maintained), which are based on the excellent **Brutefir** convolver.


## Using the measurement software

You can use a Linux o Mac OS (Homebrew) laptop.


### Dependencies

You'll need the following standard libraries:

#### Python3

    sudo apt install python3-numpy python3-matplotlib python3-scipy

Maybe you'll need to update the compilation tools and PIP (the Python packages manager):

    sudo apt install python3-pip
    sudo apt install build-essential libssl-dev libffi-dev python-dev
    sudo pip3 install --upgrade pip
    sudo pip3 install --upgrade setuptools
    sudo pip3 install sounddevice


#### AudioHumLab/audiotools

You'll need to install our audio tools from **[AudioHumLab/audiotools](https://github.com/AudioHumLab/audiotools)**

## Install 

This software is intended to be installed under the user's home folder. Please run the following commands:

    cd
    wget https://github.com/Rsantct/DRC/archive/master.zip
    unzip master
    rm master.zip
    mv DRC-master DRC
    chmod +x DRC/*.py

## Updating

    sh ~/DRC/update.sh


