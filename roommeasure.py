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

    Resulting files for every CHannel

    'CH_room_N.frd'             Measured response at mic position #N.
    'CH_room_avg.frd'           Average response from all mic positions.
    'CH_room_avg_smoothed.frd'  Average smoothed 1/24 oct below Schroeder freq,
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
                            'LR' allows the measurements of both channels
                            to be interleaved at a microphone position.
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

# Resulting measurements (all measured points for every channel)
curves = {}
# Resulting averaged curves for every channel
channels_avg= {}


################################################################################
# roommeasure.py DEFAULT parameters
################################################################################

LS.N                    = 2**17     # Sweep length in samples.
numMeas                 = 2         # Number of measurements to perform
doBeep                  = True      # Do beep warning sound before each measurement

binsFRD                 = 2**14     # Bins for .frd files
channels                = ['C']     # Channels to interleaving measurements.

Scho                    = 200       # Schroeder freq (Hz)
Noct                    = 24        # Initial 1/Noct smoothing below Scho,
                                    # then will be changed progressively until
                                    # 1/1oct at Nyquist freq.

# (i) sd.default.device and  sd.default.samplerate have default values in LS module

LS.printInfo            = True      # logsweep2TF verbose

LS.checkClearence       = False     # It is assumed that the user has check for this.

LS.TFplot               = False     # Omit default plots from the module logsweep2TF
LS.auxPlots             = False
LS.plotSmoothSpectrum   = False

# A timer to countdown between measurements, without user interaction
timer    = 0
last_seq = 0    # aux variable to check for measurement sequence changes

# Remote JACK management
jackIP      = ''
jackUser    = ''
manageJack  = False


def read_command_line():

    global doBeep, numMeas, channels, Scho, timer, jackIP, jackUser

    # an string of three comma separated numbers 'CAPdev,PBKdev,fs'
    optional_device = ''

    opcsOK = True
    for opc in sys.argv[1:]:

        if "-h" in opc.lower():
            print( __doc__ )
            sys.exit()

        elif "-nobeep" in opc.lower():
            doBeep = False

        elif "-dev" in opc.lower():
            try:
                optional_device = opc.split("=")[1]
                if not optional_device:
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

    if optional_device:
        set_sound_card(optional_device)


def print_info():

    print(f'\nsound card:\n{LS.sd.query_devices()}\n')
    print(f'fs:                 {LS.fs}')
    print(f'channels:           {channels}')
    print(f'takes per ch:       {numMeas}')
    print(f'Schroeder freq:     {Scho}')
    print(f'sweep length (N):   {LS.N}')

    if timer:
        print(f'auto progess timer: {timer} s')
    else:
        print(f'progress by user key pressing')

    if jackIP and jackUser:
        print(f'JACK IP:            {jackIP}')
        print(f'JACK user:          {jackUser}')

    print()


def user_focus_request():
    # Requesting the user to focus on this window
    print('\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('PLEASE CLICK THIS WINDOW TO RECOVER THE FOCUS')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n')
    print
    LS.sd.play(beepR, samplerate=LS.fs)
    sleep(.25)
    LS.sd.play(beepL, samplerate=LS.fs)
    sleep(1)


def do_meas_loop():
    """ Meas for every channel and stores them into the <curves> stack
    """

    def do_meas(ch='C', seq=0):

        # Do measure, by taken the positive semi-spectrum
        meas = abs( LS.do_meas()[:int(LS.N/2)] )

        # Saving the curve to a sequenced frd filename
        f, m = tools.interp_semispectrum(freq, meas, LS.fs/2, binsFRD)
        tools.saveFRD(  fname   = f'{ch}_room_{str(seq)}.frd',
                        freq    = f,
                        mag     = 20 * np.log10(m),
                        fs      = LS.fs,
                        comments= f'roommeasure.py ch:{ch} point:{str(seq)}',
                        verbose = False
                      )

        # Smoothed curve plot (this takes a while in a slow cpu)
        m_smoo = smooth(f, m, Noct, f0=Scho)
        figIdx = 10
        chs = ('L', 'R', 'C')
        if ch in chs:
            figIdx += chs.index(ch)

        # Looping CSS4 color sequence, from black (index 7)
        LS.plot_spectrum( m_smoo, semi=True, fig = figIdx,
                          label = f'{ch}_{str(seq)}',
                          color=css4_colors[(7 + seq) % 148] )

        return meas


    global curves

    # First measurement (initiates the stack)
    for ch in channels:
        warning_meas(ch=ch, seq=0)          # a warning message or counting down
        curves[ch] = do_meas(ch=ch, seq=0)

    # Do stack more measurements if so:
    for i in range(1, numMeas):
        for ch in channels:
            warning_meas(ch=ch, seq=i)
            meas = do_meas(ch=ch, seq=i)
            # stack
            curves[ch] = np.vstack( ( curves[ch], meas ) )


def do_averages():
    """ Compute the average from all raw measurements
    """

    global channels_avg

    for ch in channels:
        print( "Computing average of channel: " + ch )
        if numMeas > 1:
            # All meas average
            channels_avg[ch] = np.average( curves[ch], axis=0 )
        else:
            channels_avg[ch] = curves[ch]


def do_save_averages():
    """ Saving average to a .frd file
    """

    i = 0

    for ch in channels:

        f, m = tools.interp_semispectrum(freq, channels_avg[ch], LS.fs/2, binsFRD)
        tools.saveFRD(  fname   = f'{ch}_room_avg.frd',
                        freq    = f,
                        mag     = 20 * np.log10(m),
                        fs      = LS.fs,
                        comments= f'roommeasure.py ch:{ch} raw avg'
                      )

        # Also a smoothed version of average
        print( 'Smoothing average 1/' + str(Noct) + ' oct up to ' + \
                str(Scho) + ' Hz, then changing towards 1/1 oct at Nyq' )

        m_smoothed = smooth(f, m, Noct, f0=Scho)
        tools.saveFRD(  fname   = f'{ch}_room_avg_smoothed.frd',
                        freq    = f,
                        mag     = 20 * np.log10(m_smoothed),
                        fs      = LS.fs,
                        comments= f'roommeasure.py ch:{ch} smoothed avg' )

        # Prepare a figure with curves from all mic positions
        LS.plot_spectrum( m,          semi=True, fig=20+i,
                          color='blue', label=ch+' avg' )

        # Prepare a figure with average and smoothed average
        LS.plot_spectrum( m_smoothed, semi=True, fig=20+i,
                          color='red',  label=ch+' avg smoothed' )
        i += 1


def warning_meas(ch, seq):

    global last_seq


    def countdown(seconds):

        while seconds >= 0:
            bar = "####  " * seconds + "      " * (timer -seconds)
            print( f'    {seconds}   {bar}', end='\r' )

            if doBeep:
                if ch in ('C', 'L'):
                    LS.sd.play(beepL, samplerate=LS.fs)
                else:
                    LS.sd.play(beepR, samplerate=LS.fs)
            sleep(1)
            seconds -= 1

        print('\n\n')

    if manageJack:
        rjack.select_channel(ch)
        sleep(.2)


    if doBeep:
        if ch in ('C', 'L'):
            Nbeep = np.tile(beepL, 1 + seq)
            LS.sd.play(Nbeep, samplerate=LS.fs)
        else:
            Nbeep = np.tile(beepR, 1 + seq)
            LS.sd.play(Nbeep, samplerate=LS.fs)

    takeInfo = str(seq+1) + ' / ' + str(numMeas)
    msg = '\n\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    msg +=   f'    TAKE: {takeInfo} \n'
    msg +=    '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    if seq != last_seq:
        print(msg)

    if timer:
        msg =   '\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
        msg +=   f'    WILL MEASURE CHANNEL  < {ch} >\n'
        msg +=    '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
        print(msg)
        if seq != last_seq:
            countdown(timer)

    else:
        msg =   '\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
        msg +=   f'   PRESS ENTER TO MEASURE CHANNEL  < {ch} >\n'
        msg +=    '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
        print(msg)
        input()

    last_seq = seq


def set_sound_card(optional_device):
    """ Other than LS.sd.default parameters
        optional_device: string of three comma separated numbers 'CAPdev,PBKdev,fs'
    """

    # Setting LS.fs
    try:
        tmp = optional_device.split(",")[2].strip()
        fs = int(tmp)
        LS.fs = fs
    except:
        pass

    # CAP device
    i = int( optional_device.split(",")[0].strip() )
    # PBK device
    o = int( optional_device.split(",")[1].strip() )

    # configure LS device:
    if not LS.test_soundcard(i=i, o=o):
        sys.exit()


if __name__ == "__main__":

    # Reading command line arguments, then will update:
    #   - LS config: device, fs, and N;
    #   - doBeep, numMeas, channels, Scho, timer, jackIP, jackUser
    read_command_line()

    # Print info summary:
    print_info()

    # Connecting to remote JACK loudspeakers system:
    if jackIP and jackUser:
        from remote_jack import Remote
        # (i) Here the user will be prompted to enter the remote password
        rjack = Remote(jackIP, jackUser)
        manageJack = True

    # PREPARING things as per given options:
    # - Preparing beeps:
    beepL = tools.make_beep(f=880, fs=LS.fs)
    beepR = tools.make_beep(f=932, fs=LS.fs)

    # - Preparing log-sweep as per the updated LS parameters
    LS.prepare_sweep()

    # - Prepare a positive frequencies vector as per the selected N value.
    freq = np.linspace(0, int(LS.fs/2), int(LS.N/2))

    # Requesting the user to focus on this window
    if not timer:
        user_focus_request()

    # MAIN measure procedure and SAVING
    do_meas_loop()

    # Releases remote JACK connections
    if manageJack:
        rjack.select_channel('none')

    # COMPUTE the average from all raw measurements
    do_averages()

    # SAVING averages
    do_save_averages()

    # Plotting prepared curves
    LS.plt.show()

    # END
