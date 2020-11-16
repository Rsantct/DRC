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
    from several microphone locations.

    The resulting files for every CHannel are named as follow:

    'CH_N.frd'              Measured response at mic location #N.
    'CH_avg.frd'            Average response from all mic locations.
    'CH_avg_smoothed.frd'   Average smoothed 1/24 oct below Schroeder freq,
                            then progressively smoothed up to 1/1 oct at Nyquist.

    Usage:

        DRC_GUI.py          Launches a Graphical User Interface

      or

        roommeasure.py  [options ... ...]

         -h                 This help.

         -m=N               Number of mic locations per channel.
                            (default 2 mic takes)

         -e=XX              Power of two 2^XX to set the log-sweep length.
                            (default 2^17 == 128 K samples ~ 2 s at fs 48KHz)

         -c=X               Channel id:  L | R | LR
                            This id will form the avobe .frd filename prefix.
                            'LR' allows the measurements of both channels
                            to be interleaved at a microphone location.
                            (default 'C' will be used as filename prefix)

         -schro=XXX         Schroeder freq, influences the smoothing transition
                            for the resulting smoothed freq response file.
                            (default 200 Hz)

         -dev=cap,pbk,fs    Capture and playback devices and Fs to use.
                            (Choose the right ones by checking logsweep2TF.py -h)

         -folder=path       A folder to store the measured FRD files,
                            relative to your $HOME (default ~/rm/meas)


                            USER INTERACTION:

         -timer=N           Auto Timer N seconds between measurements.
                            Default 0 (manual) will promt the user to press ENTER.

         -nobeep            Avoids beep alerting during measuring location changes.


                            REMOTE MACHINE JACK MANAGER:

         -jip=IP            remote IP
         -juser=uname       remote username


    IMPORTANT:

    Please do a preliminary test by running the script logsweep2TF.py or
    by clicking the [test sweep] GUI button, in order to verify:

        - the sound card does not loses samples, and levels are ok.

        - the measuremet is feasible, i.e. the 'Time clearance' graph shows a
          clear spike shape (~ thousands in Y scale, without side noise).

    with the selected hardware and parameters (sample rate and sweep length).

    If bad time clearance, you'll may need to increase the sweep length.


    RESULTS:

    You can review the recorded responses by using audiotools/FRD_viewer.py:

        FRD_tool.py $(ls L_?.frd)
        FRD_tool.py $(ls L_?.frd) -24oct -f0=200  # FRD_tool can smooth


    ABOUT REMOTE MACHINE JACK MANAGEMENT:

    When measuring a JACK based loudspeaker system, this script can help
    on routing the system stereo soundcard analog input towards the convenient
    loudspeaker channel.

    So you won't need to rewire your cable from L to R and so on ;-)

    (i) Default remote sound card analog port:  'system:capture_1'
        Default remotr loudspeaker jack ports:  'brutefir:L.in', 'brutefir:R.in'

        You can modify them by editing remote_jack.yml

    (!) Be aware that you'll need a good network link to manage the remote system,
        otherwise you may experience delayed remote behavior.


    WIRING:

    Just wire your roommeasure sound card:

      out L ------>-------  Loudspeaker analog line input

      in  L ------<-------  MIC

      out R --->---
                   |        Optional reference loop for logsweep2TF.py
      in  R ---<---         time clearance checkup.

"""

# standard modules
import os
import sys
import numpy as np
from time import sleep

# logsweep2TF module (logsweep to transfer function)
try:
    import logsweep2TF as LS
except Exception as e:
    print( f'(!) ERROR loading module \'logsweep2TF.py\': {e}' )
    sys.exit()

# audiotools modules
UHOME = os.path.expanduser("~")
sys.path.append(UHOME + "/audiotools")
import tools
from smoothSpectrum import smoothSpectrum as smooth

# A list of 148 CSS4 colors to plot measured curves
from matplotlib import colors as mcolors
css4_colors = list(mcolors.CSS4_COLORS.values())    # (black is index 7)

# Resulting measurements stack (all measured points for every channel)
curves = {'freq': None, 'L': None, 'R': None}

# Resulting averaged curves for every channel
channels_avg= {'L':None, 'R':None}


################################################################################
# roommeasure.py DEFAULT parameters
################################################################################

# sd.default.device and  sd.default.samplerate have default values in LS module

LS.N                = 2**17     # Sweep length in samples.
numMeas             = 2         # Number of measurements to perform
doBeep              = True      # Do beep warning sound before each measurement
timer               = 0         # A timer to countdown between measurements,
                                # without user interaction
channels            = ['C']     # Channels to interleaving measurements.

# Results:
folder              = f'{UHOME}/rm/meas'
                                # Smoothing the resulting response:
Schro               = 200       # Schroeder freq (Hz)
Noct                = 24        # Initial 1/Noct smoothing below Schro,
                                # then will be changed progressively until
                                # 1/1oct at Nyquist freq.

LS.printInfo        = True      # logsweep2TF verbose

LS.checkClearence   = False     # It is assumed that the user has check
                                # previously for soundacard and levels setup.

# Remote JACK management
jackIP              = ''
jackUser            = ''
manageJack          = False


def print_help_and_exit():
    with open(__file__.replace('.py', '.hlp'), 'r') as f:
        print( f.read() )
    sys.exit()


def read_command_line():

    global doBeep, numMeas,  channels, Schro, timer, \
           jackIP, jackUser, folder

    # an string of three comma separated numbers 'CAPdev,PBKdev,fs'
    optional_device = ''

    opcsOK = True
    for opc in sys.argv[1:]:

        if "-h" in opc.lower():
            print_help_and_exit()

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

        elif "-sch=" in opc:
            Schro = float(opc.split('=')[-1])

        elif "-e=" in opc:
            LS.N = 2**int(opc[3:])

        elif opc[:7].lower() == '-timer=':
            timer = int( opc[7:] )

        elif opc[:5].lower() == '-jip=':
            jackIP = opc[5:]

        elif opc[:7].lower() == '-juser=':
            jackUser = opc[7:]

        elif '-f' in opc:
            folder = f'{UHOME}/rm/{opc.split("=")[-1]}'

        else:
            opcsOK = False

    if not opcsOK:
        print_help_and_exit()

    if optional_device:
        set_sound_card(optional_device)


def print_info():

    print(f'\nsound card:\n{LS.sd.query_devices()}\n')
    print(f'fs:                 {LS.fs}')
    print(f'channels:           {channels}')
    print(f'takes per ch:       {numMeas}')
    print(f'Schroeder freq:     {Schro}')
    print(f'sweep length (N):   {LS.N}')

    if timer:
        print(f'auto progess timer: {timer} s')
    else:
        print(f'progress by user key pressing')

    if jackIP and jackUser:
        print(f'JACK IP:            {jackIP}')
        print(f'JACK user:          {jackUser}')


    print(f'FRDs folder:        {folder}')
    print()


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


def print_console_msg(msg):
    tmp = '\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    tmp +=  f'{msg}\n'
    tmp +=  '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
    print(tmp)


def do_beep(ch='C', times=1, blocking=True):

    if ch in ('C', 'L'):
        Nbeep = np.tile(beepL, times)
        LS.sd.play(Nbeep, samplerate=LS.fs, blocking=blocking)

    elif ch in ('R'):
        Nbeep = np.tile(beepR, times)
        LS.sd.play(Nbeep, samplerate=LS.fs, blocking=blocking)


def console_prompt(ch, seq):
    """ Promts the user through by the console
    """

    def countdown(s):
        while s:
            bar = "####  " * s + "      " * (timer - s)
            print( f'    {s}   {bar}', end='\r' )
            if doBeep:
                do_beep(ch)
            sleep(1)
            s -= 1
        print('\n\n')


    if doBeep:
        do_beep(ch, seq + 1)

    if timer:
        print_console_msg(f'WILL MEASURE CHANNEL  < {ch} >')
        countdown(timer)
    else:
        print_console_msg(f'PRESS ENTER TO MEASURE CHANNEL  < {ch} >')
        input()


def gui_prompt(ch, seq, gui_trigger, gui_msg):
    """ Prompts the user through by the GUI
        gui_trigger:    a GUI.threading.Event flag that trigger to meas.
        gui_msg:        a GUI.label_string_variable to prompt the user.
    """

    def countdown(s):
        while s:
            if gui_msg:
                tmp = f'will meas at location #{seq+1}  [ {ch} ]  <<< {s} s >>>'
                gui_msg.set(tmp)
                if doBeep:
                    do_beep(ch)
            sleep(1)
            s -=1

    if doBeep:
        do_beep(ch, seq)

    if timer:
        countdown(timer)
    else:
        gui_msg.set(f'will meas at location #{seq+1}  [{ch}]  < PRESS ANY KEY >')
        print(f'(rm) WAITING FOR TRIGGER meas #{seq+1}_ch:{ch}')
        gui_trigger.wait()
        print(f'(rm) RESUMING, meas #{seq+1}_ch:{ch}')
        gui_trigger.clear()

    gui_msg.set(f'computing location #{seq+1}  [ {ch} ] (please wait)')


def LS_meas(ch, seq):

    # Order LS to do the measurement
    LS.do_meas()

    f, mag = LS.DUT_FRD
    magdB = 20 * np.log10( mag )

    # Saving the curve to a sequenced frd filename
    tools.saveFRD(  fname   = f'{folder}/{ch}_{str(seq)}.frd',
                    freq    = f,
                    mag     = magdB,
                    fs      = LS.fs,
                    comments= f'roommeasure.py ch:{ch} loc:{str(seq)}',
                    verbose = False
                  )

    # Plotting
    figIdx = 10
    chs = ('L', 'R', 'C')
    if ch in chs:
        figIdx += chs.index(ch)

    # Will choose a color by selecting the CSS4 color sequence, from black (index 7)
    c = {   'magdB': magdB,
            'color': css4_colors[(7 + seq) % 148],
            'label': f'{ch}_{str(seq)}'             }

    LS.plot_FRDs( f, (c,),  title=f'{os.path.basename(folder)} ({ch})',
                            figure=figIdx,
                             png_fname=f'{folder}/{ch}.png'
                )

    return f, mag  # LS.DUT_FRD is given in lineal magnitude not dB


def do_meas_loop(gui_trigger=None, gui_msg=None):
    """ Meas for every channel and stores them into the <curves> stack
        Optional:
            gui_trigger:    a GUI.threading.Event flag that trigger to meas.
            gui_msg:        a GUI.label_string_variable to prompt the user.
    """

    # 'curves' is a numpy stack of measurements per channel
    global curves

    # Alerting the user
    if gui_msg:
        gui_msg.set(f'GOING TO MEASURE AT  {numMeas}  LOCATIONS ...')
        sleep(.5)
    else:
        print_console_msg(f'GOING TO MEASURE AT  {numMeas}  LOCATIONS ...')
    if doBeep:
        for i in range(3):
            do_beep('L')
            do_beep('R')
    sleep(.5)


    for seq in range(numMeas):

        if gui_trigger:
            gui_msg.set(f'LOCATION: {str(seq+1)} / {str(numMeas)}')
            sleep(1)
        else:
            print_console_msg(f'MIC LOCATION: {str(seq+1)}/{str(numMeas)}')

        for ch in channels:

            if manageJack:
                rjack.select_channel(ch)
                sleep(.2)

            # gui
            if gui_trigger:
                gui_prompt(ch, seq, gui_trigger, gui_msg)

            # console
            else:
                console_prompt(ch, seq)

            # DO MEASURE AND STACK RESULTS
            f, mag = LS_meas(ch, seq)       # (i) mag is given lineal
            #
            curves['freq'] = f
            #
            if seq == 0:
                curves[ch] = mag
            else:
                curves[ch] = np.vstack( ( curves[ch], mag ) )

    if manageJack:
        rjack.select_channel('')

    if gui_msg:
        gui_msg.set('MEASURING COMPLETED.')
        sleep(1)
    else:
        print_console_msg('MEASURING COMPLETED.')


def do_averages():
    """ Compute the average from all raw measurements,
        saving to .frd and plotting
    """

    # Computing averages if more than one measurement
    for ch in channels:
        print( "Computing average of channel: " + ch )
        if numMeas > 1:
            # All meas average
            channels_avg[ch] = np.average( curves[ch], axis=0 )
        else:
            channels_avg[ch] = curves[ch]

    f = curves['freq']

    figIdx = 0
    for ch in channels:

        avg_mag     = channels_avg[ch]
        avg_mag_dB  = 20 * np.log10( avg_mag )

        tools.saveFRD(  fname   = f'{folder}/{ch}_avg.frd',
                        freq    = f,
                        mag     = avg_mag_dB,
                        fs      = LS.fs,
                        comments= f'roommeasure.py ch:{ch} raw avg' )

        # Also a progressive smoothed version of average
        print( 'Smoothing average 1/' + str(Noct) + ' oct up to ' + \
                str(Schro) + ' Hz, then changing towards 1/1 oct at Nyq' )

        avg_mag_progSmooth      = smooth(f, avg_mag, Noct, f0=Schro)
        avg_mag_progSmooth_dB   = 20 * np.log10(avg_mag_progSmooth)

        tools.saveFRD(  fname   = f'{folder}/{ch}_avg_smoothed.frd',
                        freq    = f,
                        mag     = avg_mag_progSmooth_dB,
                        fs      = LS.fs,
                        comments= f'roommeasure.py ch:{ch} smoothed avg' )

        # Prepare the average curve ...
        c1 = {  'magdB': avg_mag_dB,
                'label': f'{ch} avg',
                'color': 'blue'         }

        # ... and adding the smoothed average curve
        c2 = {  'magdB': avg_mag_progSmooth_dB,
                'label': f'{ch} avg smoothed',
                'color': 'red'                  }

        LS.plot_FRDs( f, (c1,c2),   title=f'{os.path.basename(folder)} ({ch})',
                                    figure= 20 + figIdx,
                                    png_fname=f'{folder}/{ch}_avg.png' )

        figIdx += 1


def connect_to_remote_JACK(jackIP, jackUser, pwd=None):

    global manageJack, rjack

    from remote_jack import Remote

    # (i) Here the user will be prompted to enter the remote password
    try:
        rjack = Remote(jackIP, jackUser, password=pwd)
        manageJack = True
        print_console_msg(f'Connected to remote Jack machine {jackIP}')

    except Exception as e:
        print_console_msg(f'ERROR connecting to remote Jack machine {jackIP}')
        manageJack = False

    return manageJack


def prepare_frd_folder():

    global folder

    if not os.path.exists(folder):
        os.makedirs(folder)
        print_console_msg(f'output to \'~{folder.replace(UHOME, "")}\'' )

    else:
        i=1
        while True:
            if not os.path.exists(f'{folder}_{i}'):
                os.makedirs(f'{folder}_{i}')
                folder = f'{folder}_{i}'
                print_console_msg(f'output to \'~{folder.replace(UHOME, "")}\'' )
                break
            i += 1
            if i >= 100:
                print_console_msg(f'too much \'~{folder.replace(UHOME, "")}_xx\' folders :-/' )
                return False

    return True


if __name__ == "__main__":

    # Reading command line arguments, then will update:
    #   - LS config: device, fs, and N;
    #   - doBeep, numMeas, channels, Schro, timer, jackIP, jackUser
    read_command_line()

    # - Prepare output FRD folder:
    if not prepare_frd_folder():
        print_console_msg('Please check your folders tree')
        sys.exit()

    # Print info summary:
    print_info()

    # Connecting to remote JACK loudspeakers system:
    if jackIP and jackUser:
        connect_to_remote_JACK(jackIP, jackUser)

    # PREPARING things as per given options:
    # - Preparing beeps:
    beepL = tools.make_beep(f=880, fs=LS.fs, duration=0.05)
    beepR = tools.make_beep(f=932, fs=LS.fs, duration=0.05)

    # - Preparing log-sweep as per the updated LS parameters
    LS.prepare_sweep()

    # MAIN measure procedure and SAVING
    do_meas_loop()

    # Releases remote JACK connections
    if manageJack:
        rjack.select_channel('none')

    # COMPUTE the average from all raw measurements
    do_averages()

    # Plotting prepared curves
    LS.plt.show()

    # END
