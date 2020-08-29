#!/usr/bin/env python3

# Copyright (c) 2019 Rafael Sánchez
# This file is part of 'Rsantct.DRC', yet another DRC FIR toolkit.
#
# 'Rsantct.DRC' is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# 'Rsantct.DRC' is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with 'Rsantct.DRC'.  If not, see <https://www.gnu.org/licenses/>.

"""
    Gets the stationary frequency response from an in-rooom loudspeaker,
    from several microphone positions.

    Resulting files:

    'room_N.frd'             Measured response at micro position #N.
    'room_avg.frd'           Average response from all micro positions.
    'room_avg_smoothed.frd'  Average smoothed 1/24 oct below Schroeder freq,
                             then progressively becoming 1/1 oct at Nyquist.

    Usage:

        roommeasure.py  [options ... ...]

         -h                 This help

         -m=N               Number of takes (per channel)
                            (default 2 takes)

         -e=XX              Power of two 2^XX to set the log-sweep length.
                            (default 2^17 )

         -c=X               Channel id:  L | R | LR
                            This id will form the .frd filename prefix.
                            'LR' allows interleaving both channels measures in
                            a microphone position.
                            (default C will be used as filename prefix)

         -s=XXX             Shroeder freq, influences the smoothing transition.
                            (default 200 Hz)

         -dev=cap,pbk,fs    Capture and playback devices and Fs to use
                            (Choose the right ones by checking logsweep2TF.py -h)


                            USER INTERACTION:

         -timer=N           Auto Timer N seconds between measurements
                            (default no auto timer, the user must press ENTER)

         -nobeep            Avoids beep alerting during measuring position changes.


                            REMOTE MACHINE JACK MANAGER:

         -jip=IP            remote IP
         -juser=uname       remote username



    IMPORTANT:

    Please do a preliminary test by using logsweep2TF.py, in order to verify:

    - The sound card does not loses samples, and levels are ok.

    - The measuremet is feasible (Time clearance) with the selected parameters.


    OPTIONAL:

    You can review the recorded responses by using audiotools/FRD_viewer.py:

        FRD_tool.py $(ls L_room_?.frd)
        FRD_tool.py $(ls L_room_?.frd) -24oct -f0=200  # FRD_tool will smooth

"""

# standard modules
import os
import sys
import numpy as np
from scipy import interpolate
from time import sleep

# logsweep2TF module (logsweep to transfer function)
try:
    import logsweep2TF as LS
except:
    print( "(!) It is needed logsweep2TF.py" )
    sys.exit()

# audiotools modules
HOME = os.path.expanduser("~")
sys.path.append(HOME + "/audiotools")
import tools
from smoothSpectrum import smoothSpectrum as smooth

# A list of 148 CSS4 colors to plot measured curves
from matplotlib import colors as mcolors
css4_colors = list(mcolors.CSS4_COLORS.values())    # (black is index 7)

################################################################################
# roommeasure.py DEFAULT parameters
################################################################################

LS.N                    = 2**17     # Sweep length in samples.
numMeas                 = 2         # Number of measurements to perform
doBeep                  = True      # Do beep warning sound before each measurement

binsFRD                 = 2**14     # Bins for .frd files
channels                = 'C'       # Channels to interleaving measurements.

Scho                    = 200       # Schroeder freq (Hz)
Noct                    = 24        # Initial 1/Noct smoothing below Scho,
                                    # then will be changed progressively until
                                    # 1/1oct at Nyquist freq.

#LS.sd.default.xxxx                 # logsweep2TF has its owns default values
selected_card           = LS.selected_card

LS.printInfo            = True      # logsweep2TF verbose

LS.checkClearence       = False     # It is assumed that the user has check for this.

LS.TFplot               = False     # Omit default plots from the module logsweep2TF
LS.auxPlots             = False
LS.plotSmoothSpectrum   = False

# A timer to wait between measurements, without user interaction
timer = 0

# Remote JACK management
jackIP      = ''
jackUser    = ''
manageJack  = False


def countdown(seconds):

    while seconds:
        bar = "####  " * seconds + "      " * (timer -seconds)
        print( f'    {seconds}   {bar}', end='\r' )

        if doBeep:
            if ch in ('C', 'L'):
                LS.sd.play(beepL, samplerate=fs)
            else:
                LS.sd.play(beepR, samplerate=fs)
        sleep(1)
        seconds -= 1

    print('\n\n')

def interpSS(freq, mag, Nbins):
    """ Interpolates a semi-spectrum curve into a new Nbins length
        linespaced frequencies vector.
    """
    freqNew  = np.linspace(0, fs/2, Nbins)
    # Interpolator function
    funcI = interpolate.interp1d(freq, mag, kind="linear", bounds_error=False,
                         fill_value="extrapolate")
    # Interpolated values:
    return freqNew, funcI(freqNew)


def doMeas(ch='C', seq=0):

    # Do measure, by taken the positive semi-spectrum
    meas = abs( LS.do_meas(windosweep, sweep)[:int(N/2)] )

    # Saving the curve to a sequenced frd filename
    f, m = interpSS(freq, meas, binsFRD)
    tools.saveFRD( ch + '_room_'+str(seq)+'.frd',f, 20*np.log10(m), fs=fs,
                   comments='roommeasure.py ch:' + ch + ' point:' + str(seq),
                   verbose=False )

    # Smoothed curve plot (this takes a while in a slow cpu)
    m_smoo = smooth(f, m, Noct, f0=Scho)
    figIdx = 10
    chs = ('L', 'R', 'C')
    if ch in chs:
        figIdx += chs.index(ch)

    # Looping CSS4 color sequence, from black (index 7)
    LS.plot_spectrum( m_smoo, semi=True, fig = figIdx,
                      label = ch + '_' + str(seq),
                      color=css4_colors[(7 + seq) % 148] )
    return meas


def warning_meas(ch, seq):

    if manageJack:
        rjack.select_channel(ch)


    if doBeep:
        if ch in ('C', 'L'):
            Nbeep = np.tile(beepL, 1 + seq)
            LS.sd.play(Nbeep, samplerate=fs)
        else:
            Nbeep = np.tile(beepR, 1 + seq)
            LS.sd.play(Nbeep, samplerate=fs)

    if timer:
        msg =   '\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
        msg +=   f'WILL MEASURE CHANNEL  < {ch} >  ( {str(seq+1)}/{str(numMeas)})\n'
        msg +=    '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
        print(msg)
        countdown(timer)

    else:
        msg =   '\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
        msg +=   f'PRESS ENTER TO MEASURE CHANNEL  < {ch} >  ( {str(seq+1)}/{str(numMeas)})\n'
        msg +=    '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
        print(msg)
        input()


def make_beep(f=1000, fs=44100, dBFS=-9.0, dur=0.10, head=0.01, tail=0.03):
    """ a simple waveform to be played as an alert before starting to measure
    """
    head = np.zeros( int(head * fs) )
    tail = np.zeros( int(tail * fs) )
    x = np.arange( fs * dur )               # a bare silence array
    y = np.sin( 2 * np.pi * f * x / fs )    # the waveform itself
    y = np.concatenate( [head, y, tail] )   # adding silences
    y *= 10 ** (dBFS/20.0)                  # attenuation as per dBFS
    return y


if __name__ == "__main__":


    # Reading command line arguments:
    opcsOK = True
    for opc in sys.argv[1:]:

        if "-h" in opc.lower():
            print( __doc__ )
            sys.exit()

        elif "-nobeep" in opc.lower():
            doBeep = False

        elif "-dev" in opc.lower():
            try:
                selected_card = opc.split("=")[1]
                if not selected_card:
                    print( __doc__ )
                    sys.exit()
            except:
                print( __doc__ )
                sys.exit()

        elif "-m=" in opc:
            numMeas = int(opc[3:])

        elif "-c=" in opc:
            channels = [x for x in opc[3:]]

        elif "-s=" in opc:
            Scho = int(opc[3:])

        elif "-e=" in opc:
            LS.N = 2**int(opc[3:])

        elif opc[:7].lower() == '-timer=':
            timer = int( opc[7:] )

        elif opc[:5].lower() == '-jip=':
            jackIP = opc[5:]

        elif opc[:7].lower() == '-juser=':
            jackUser = opc[7:]

        else:
            opcsOK = False

    if not opcsOK:
        print( __doc__ )
        sys.exit()


    # Setting sounddevice
    LS.sd.default.channels     = 2
    LS.sd.default.samplerate   = float(LS.fs)
    if selected_card:
        i = selected_card.split(",")[0].strip()
        o = selected_card.split(",")[1].strip()
        try:    fs = int(selected_card.split(",")[2].strip())
        except: pass
        if i.isdigit(): i = int(i)
        if o.isdigit(): o = int(o)
        #  If command line sound device fails.
        if not LS.test_soundcard(i=i, o=o):
            sys.exit()


    # Reading N and fs as pet set in module LS when reading command line options
    N             = LS.N
    fs            = LS.fs


    # Optional beeps
    beepL = make_beep(f=880, fs=fs)
    beepR = make_beep(f=932, fs=fs)


    #    recovering the focus to this terminal window
    print('\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('PLEASE CLICK THIS WINDOW TO RECOVER THE FOCUS')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n')
    print
    LS.sd.play(beepR, samplerate=fs)
    sleep(.25)
    LS.sd.play(beepL, samplerate=fs)
    sleep(1)


    # Optional connection to a remote JACK server
    if jackIP and jackUser:
        from remote_jack import Remote
        rjack = Remote(jackIP, jackUser)
        manageJack = True


    # positive frequencies vector as per the selected N value.
    freq = np.linspace(0, fs/2, N/2)


    # 1. Log-sweep preparing
    windosweep, sweep = LS.make_sweep()


    # 2. Start measuring, by accumulating into an averages stack 'SSs'
    SSs = {}
    SSsAvg = {}
    # Waits for pressing ENTER
    for ch in channels:
        warning_meas(ch=ch, seq=0)
        SSs[ch] = doMeas(ch=ch, seq=0)
    #    Adding more measures if so:
    for i in range(1, numMeas):
        for ch in channels:
            # Waits for pressing ENTER
            warning_meas(ch=ch, seq=i)
            meas = doMeas(ch=ch, seq=i)
            # stack on 'SSs'
            SSs[ch] = np.vstack( ( SSs[ch], meas ) )

    if manageJack:
        rjack.select_channel('none')


    # 3. Compute the average from all raw measurements
    for ch in channels:
        print( "Computing average of channel: " + ch )
        if numMeas > 1:
            # All meas average
            SSsAvg[ch] = np.average(SSs[ch], axis=0)
        else:
            SSsAvg[ch] = SSs[ch]


    # 4. Saving average to .frd file
    i = 0
    for ch in channels:
        f, m = interpSS(freq, SSsAvg[ch], binsFRD)
        tools.saveFRD( ch + '_room_avg.frd', f, 20*np.log10(m) , fs=fs,
                       comments='roommeasure.py ch:' + ch + ' raw avg' )

        # 5. Also a smoothed version of average
        print( "Smoothing average 1/" + str(Noct) + " oct up to " + \
                str(Scho) + " Hz, then changing to 1/1 oct at Nyq" )
        m_smoothed = smooth(f, m, Noct, f0=Scho)
        tools.saveFRD( ch + '_room_avg_smoothed.frd',
                       f,
                       20 * np.log10(m_smoothed),
                       fs=fs,
                       comments='roommeasure.py ch:' + ch + ' smoothed avg' )

        # 6. Prepare a figure with curves from all placements
        LS.plot_spectrum( m,          semi=True, fig=20+i,
                          color='blue', label=ch+' avg' )
        #    Prepare a figure with average and smoothed average
        LS.plot_spectrum( m_smoothed, semi=True, fig=20+i,
                          color='red',  label=ch+' avg smoothed' )
        i += 1


    # 7. plotting prepared curves
    LS.plt.show()


    # END
