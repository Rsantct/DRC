# DRC

This soft is intended to measure a loudspeaker's in-room response, then calculate a FIR filter to perform DRC equalization (digital room correction). You'll ned to use a convolver inserted in the loudspeakers signal path, such **Brutefir** as used [here](https://github.com/AudioHumLab/pe.audio.sys)

The applied test signal will be a **log sweep** chirp.

## Testing your sound card settings

The main meas script is **`logsweep2TF.py`**. It is based on a public licensed Matlab program from Richard Mann and John Vanderkooy, published at [linearaudio.net](https://linearaudio.net/downloads) (Vol.13).

This software not only performs the freq response calculation of your sound system, it also provides a **_time clearance_** checking of the meassurement chain, depending on the total latency and the selected log-sweep lenght.

<img src="https://github.com/Rsantct/DRC/blob/master/doc/time_clearance.png" width="480">

Graphical information will help you also to detect inaudible gaps that can appear from your hardware stuff. The following both channels direct loop ilustrates this anomalie:

<img src="https://github.com/Rsantct/DRC/blob/master/doc/gaps_in_recorded.jpg" width="480">



## Multipoint measurement


The script **`roommeasure.py`** allows to perform **_stationary measurements in several mic locations_**, then resulting an averaged frequency response in `.frd` file format.

The spatial amplitude for mic locations relies in the user criteria, depending on the listening scenario.


### JACK management

When measuring a [JACK based loudspeaker system](https://github.com/AudioHumLab), **`roommeasure.py`** can help on routing the loudspeaker system stereo soundcard analog input towards the convenient loudspeaker channel. So you won't need to rewire your cable from L to R and so on ;-)

## GUI appearance:

<img src="https://github.com/Rsantct/DRC/blob/master/doc/roommeasure_GUI_screen_1.png" width="640">


Testing the log-sweep recording:

<img src="https://github.com/Rsantct/DRC/blob/master/doc/test_sweep.png" width="800">


A multipoint measurement:

<img src="https://github.com/Rsantct/DRC/blob/master/doc/multipoint_sample.png" width="800">


## DRC EQ filter calculation

The script **`roomEQ.py`** is in charge to calculate the FIR filter for DRC EQ, from a given `.frd` freq response file, as the one provided from **`roommeasure.py`**, or other software e.g : ARTA or Room EQ Wizard.

**`roomEQ.py`** allows to generate FIR with variable length (resolution) and/or sampling frequency.

The **reference level** on which it is applied the EQ is automatically detected, but you can manually choose it after visualizing the proposed curves.


```
    roomEQ.py

    Calculates room equalizer FIRs from a given in-room freq. responses,
    usually an averaged ones as the provided from 'roommeasure.py'.

    Usage:

        roomEQ.py response.frd [response2.frd ...]   [ options ]

            -fs=        Output FIR sampling freq (default 48000 Hz)

            -e=         Exponent 2^XX for FIR length in taps.
                        (default 15, i.e. 2^15=32 Ktaps)

            -ref=       Reference level in dB (default autodetected)

            -schro=     Schroeder freq. (default 200 Hz)

                        Gaussian windows to progressively limit positive EQ:

            -wLfc=      Low window center freq  (default: at 5 oct ~ 630 Hz)

            -wHfc=      High window center freq (default: at 5 oct ~ 630 Hz)

            -wLoct=     Span in octaves for the left side of wL  (def: 5 oct)

            -wHoct=     Span in octaves for the right side of wH (def: 5 oct)

            -noPos      Does not allow positive gains at all

            -doFIR      Generates the pcm FIR after estimating the final EQ.


    ABOUT POSITIVE EQ GAIN:

    If desired, then a gaussian window will be used to limit positive gains.

    Two windows are available: wL works on the lower freq band, wH on highs.

    These windows by default are centered at 5 octaves (630Hz) with symmetric
    span shapes of 5 oct, so minimized at 20 Hz and 20 Khz ends.

    If the measured level extends over most of the range 20 Hz ~ 20 KHz
    (the 10 octaves audio band), the default shape usually works fine.

    If the measured response has significant limitations on the upper band,
    you may want to extend the right side of wH by setting wHoct > 5.

    Usually the default 5 oct left side window span (low freq) works fine.

```

Example of a very strong room mode in the listening area:

<img src="https://github.com/Rsantct/DRC/blob/master/doc/roomEQ_hard-modes.png" width="800">


## FIR application

The obtained FIR filter, must be loaded into a convolver as **Brutefir** in Linux, or into a generic reverb plugin as Wave's IR1 in a DAW, or into a hardware convolver as miniDSP.

Here we propose the evolutions [pe.audio.sys](https://github.com/AudioHumLab) or [pre.di.c](https://github.com/AudioHumLab) from the original project [FIRtro](https://github.com/AudioHumLab/FIRtro/wiki/01---Introducción) (currently not maintained), which are based on the excellent **Brutefir** convolver.

<img src="https://github.com/Rsantct/DRC/blob/master/doc/DRC_in_action.png" width="480">


## Using the measurement software

You can use a Linux or Mac OS laptop, equipped with a suitables sound card and measurement mic.


### Dependencies

You'll need the following standard libraries (Linux Debian flavor install commands are shown below).

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

    cd ~
    curl -LO https://raw.githubusercontent.com/Rsantct/DRC/master/update-DRC.sh
    sh update-DRC.sh master

## Updating

    sh ~/DRC/update-DRC.sh


