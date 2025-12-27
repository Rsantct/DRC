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

# CREDITS:
# 'An Open-Source Electroacoustic Measurement System'
# Richard Mann and John Vanderkooy
# March 2017, Audio Research Group, University of Waterloo


"""
    logsweep2TF.py

    Computes the TF Transfer Function from a Device-Under-Test, through by the
    deconvolution of an excitation log-sweep signal and the mic captured one.


    Sound card wiring:

      out L ------>-------  DUT (loudspeaker analog line input)

      in  L ------<-------  MIC

      out R --->---+
                   |        Optional reference loop for
      in  R ---<---+        time clearance checkup.


    Usage:      python3 logsweep2TF.py  [options ... ...]

    -h                  Help

    -sc                 Request a sound card and proof.

    -dev=cap,pbk,fs     Sund devices and fs to use.
                        Use -h to list the available ones.

    -eXX                Power of 2 that determines the total lenght N of the
                        test log-sweep. Default 2^18 = 256K samples ~ 4 sec


    -noclearance        Ommit time clearance validation.

    -nosmooth           Don't smooth freq response. Default smooth at 1/24 oct

    -auxplots           plot aux graphs (work in progress)

"""
#-------------------------------------------------------------------------------
#-------------------------------- CREDITS: -------------------------------------
#-------------------------------------------------------------------------------
# This script is based on the Matlab Open Source code:
#   'An Open-Source Electroacoustic Measurement System'
#   Richard Mann and John Vanderkooy, March 2017,
#   Audio Research Group, University of Waterloo
#
# https://linearaudio.net/volumes/2282
# https://linearaudio.net/downloads
# https://linearaudio.net/sites/linearaudio.net/files/vol%2013%20rm%26jvdk%20readme%26m-files%20p1.zip
# https://linearaudio.net/sites/linearaudio.net/files/vol%2013%20rm%26jvdk%20readme%26m-files%20p2.zip
#
#
#   Notes:
#   - calibration options are not considered here
#   - windowing for quasi-anechoic analisys is not performed here
#

#---------------------------- IMPORTING MODULES: -------------------------
import  os
import  sys
from    time        import time
import  sounddevice as sd
from    fmt         import Fmt

# https://matplotlib.org/faq/howto_faq.html#working-with-threads
import  matplotlib

# Later we will be able to call matplotlib.use('Agg') to replace the regular
# display backend (e.g. 'Mac OSX') by the dummy one 'Agg' in order to avoid
# incompatibility when threading this module, e.g. when using a Tcl/Tk GUI.

import  matplotlib.pyplot as plt

from    matplotlib.ticker   import EngFormatter
from    numpy               import *                                # for code clarity
from    scipy.signal        import correlate as signal_correlate    # to differentiate from numpy

# scipy.signal.correlate shows a FutureWarning, we do inhibit it:
import  warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

UHOME = os.path.expanduser("~")
sys.path.append(UHOME + "/audiotools")
from    smoothSpectrum import smoothSpectrum as smooth
import  tools

#-------------------------------------------------------------------------------
#----------------------------- DEFAULT OPTIONS: --------------------------------
#-------------------------------------------------------------------------------
select_card         = False
selected_card       = ''
checkClearence      = True

printInfo           = True

do_plot             = True      # recorded, time clearance, freq response plots
aux_plot            = False     # currently only for the prepared sweep plot
png_folder          = f'{UHOME}/DRC'

# Prepare a flat MIC response
mic_response_path   = ''
mic_response        = array([[2, 200, 2000, 20000], [0, 0, 0, 0]]).transpose()
using_mic_response  = False

#-------------------------------------------------------------------------------
#----------------------------- DEFAULT PARAMETERS: -----------------------------
#-------------------------------------------------------------------------------
sig_frac    = 0.5               # Fraction of full scale applied to play the sweep.
fs          = 48000             # Must ensure that sound driver accepts.
N           = 2**18             # Lenght of the total sequence, make this
                                # larger if there is insufficient time clearance
clipWarning = -3.0              # dBFS warning when capturing

system_type = 'electronic'      # 'acoustic', 'electronic', 'level-dependent'
Po          = 2e-5              # SPL reference pressure
c           = 343               # speed of sound

FRDpoints   = 1000              # logspaced freq points for output .frd files
Noct        = 24                # smoothing 1/N oct for freq response data

yplotmax    = 6                 # TF plots above 0 dB
yplotspan   = 54                # total scale of TF plots

#----------------- System calibration factor CF for dut ------------------------
power_amp_gain  = 10            # V/V acoustic
mic_cal         = 0.012         # V/Pa acoustic
mic_preamp_gain = 10.0          # V/V acoustic
Vw              = 1.0           # 2.83 V/watt8ohms acoustic Leave this=1 if not wanted
electronic_gain = 1.0           # total gain in series with electronic system
#------------------- Enter value for your soundcard: ---------------------------
S_dac = 1.0
S_adc = 1.0
## S_dac=-1.22;         % UCA202
## S_adc=-1.40;         % UCA202 (gain=3 Windows 7). This avoids ADC overload
## S_dac=0.98;          % UA-1ex
## S_adc=0.5;           % UA-1ex
## S_dac=2.17*sqrt(2);  % UA-25 May have internal +/-5V supply?
## S_adc=+6.0;          % UA-25 also high.
## S_dac=+1.59;         % Focusrite 2i2 No, it does not inverts its DAC as article says
## S_adc=+1.16;         % Focusrite 2i2 line input gain @ 12:00 o'clock
## S_dac=+1.148;        % USB Dual Pre peak volts out for digital Full Scale
## S_adc=+1.49;         % USB Dual Pre JV pot minimum (gain=3, Windows 7)


def plot_mic_compensation(hz, mic_db, raw_db, corrected_db):
    """
        <doplot> controls plt.show() if no more figures are to be plotted
    """

    plt.figure('MIC correction', figsize=(6, 3))

    plt.semilogx(hz, mic_db,       label='MIC response',       linestyle='--', color='brown')
    plt.semilogx(hz, corrected_db, label='Corrected response', linestyle='-', linewidth=2, color='blue')
    plt.semilogx(hz, raw_db,       label='Raw response',       linestyle='-', alpha=0.6, color='gray')

    plt.title(f'MIC corrected response \n{os.path.basename(mic_response_path)}', fontsize=10)
    plt.xlabel('Freq (Hz)')
    plt.ylabel('Amplitude (dB)')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.legend()
    plt.xlim(20, 20000)
    plt.ylim(-60,10)
    plt.tight_layout()
    plt.savefig(f'{png_folder}/mic_correction.png')


def set_mic_response():

    global mic_response, using_mic_response

    if os.path.isfile(mic_response_path):

        using_mic_response = False

        try:
            # readFRD returns a tuple (frd, fs) where frd is an array of Hz:dB
            mic_response_candidate, _ = tools.readFRD(mic_response_path)

            if mic_response_candidate.shape[0] > 1:

                mic_response = mic_response_candidate
                using_mic_response = True
                print(f'{Fmt.BLUE}MIC response was loaded{Fmt.END}')

                # shifting the usual flat region curve 200 Hz ~ 4000 Hz to 0 dB
                flat_offset_dB = tools.get_avg_flat_region(mic_response, 200, 4000)
                mic_response[:, 1] -= flat_offset_dB
                print(f'{Fmt.BLUE}{Fmt.BOLD}MIC response was shifted {flat_offset_dB:.2f} dB so that the flat region is 0 dB{Fmt.END}')

        except Exception as e:
            print(f'{Fmt.RED}** BAD ** MIC calibration file, using a flat response.{Fmt.RED}')
            print(f'{Fmt.GRAY}{str(e)}{Fmt.END}')

    else:
        print(f'{Fmt.RED}MIC file NOT FOUND: {mic_response_path}{Fmt.END}')


def get_mic_corrected_response(raw_frd, doplot=False):

    # extract freq and mag arrays from the given `xfrd` tuple
    raw_freq, raw_db = raw_frd

    # extract freq and mag arrays from the `mic_response` 2D array
    mic_freq = mic_response[:, 0]
    mic_db   = mic_response[:, 1]

    # Interpolate mic response to the given raw_freq points.
    # As log spaced audio freq points can be widely separated, it is
    # preferred to interpolate over the logarithm of the frequency.
    mic_db_interp = interp(log10(raw_freq), log10(mic_freq), mic_db)

    # Finally, correct the given frd with the mic_frd
    corrected_db = raw_db - mic_db_interp

    print(f'{Fmt.GREEN}MIC correction was applied.{Fmt.END}')

    if doplot:
        plot_mic_compensation(raw_freq, mic_db_interp, raw_db, corrected_db)

    return raw_freq, corrected_db


def get_avail_input_channels():
    n = 0
    try:
        n = sd.query_devices(kind='input').get('max_input_channels', 0)
    except Exception as e:
        print(f'ERROR getting input device: {str(e)}')
        sys.exit()
    return n


def choose_soundcard():

    result = False

    tries = 0
    while not result and tries < 3:
        print( "\n    SYSTEM SOUND DEVICES:\n" )
        print( sd.query_devices() )
        print()
        print( "    Select capture  device: ", end='' ); i = int(input())
        print( "    Select playback device: ", end='' ); o = int(input())
        result = test_soundcard(i,o)
        tries += 1

    return result


def test_soundcard(i="default",o="default", fs=fs, ch=2):

    ch = get_avail_input_channels()

    dummy1sec = zeros(int(fs))

    print( 'Trying:' )
    print(f'    {sd.query_devices(i, kind="input" )["name"]}')
    print(f'    {sd.query_devices(o, kind="output")["name"]}')

    try:
        sd.default.device = i, o
    except Exception as e:
        print( f'(!) Error accesing devices [{i},{o}]: {e}' )
        return e

    try:
        chk_rec = sd.check_input_settings (i, channels=ch, samplerate=float(fs))
        chk_pb  = sd.check_output_settings(o, channels=ch, samplerate=float(fs))
        print( f'Sound card parameters OK' )
    except Exception as e:
        print( f'(!) Sound card [{i},{o}] ERROR: {e}' )
        return e

    try:
        dummy = sd.playrec(dummy1sec, samplerate=fs, channels=ch)
        print( 'Sound device settings are supported' )
    except Exception as e:
        print( f'(!) FAILED to playback and recording on selected device: {e}' )
        return e

    return 'ok'


def do_print_info():

    print( "\n--- SYSTEM SOUND DEVICES:" )
    print( sd.query_devices() )
    rec, pb = sd.default.device
    print( f"    Using '{str(pb)}' to PLAYBACK" )
    print( f"          '{str(rec)}' to RECORD")
    print( f"               LEFT  <--- [ DUT ]" )
    print( f"               RIGHT <--- [ REF ]" )
    print( f"\n--- Parameters:" )
    sig_frac_dBFS = round(20 * log10(sig_frac), 2)
    print( 'Amplitude:      ' + str(sig_frac) + ' (' + str(sig_frac_dBFS) + ' dBFS)' )
    print( 'fs:             ' + str(fs) + ' Hz' )
    print( 'N:              ' + str(N) + ' (test signal total lenght in samples)' )
    print( 'Duration:       ' + str( round((N/float(fs)), 2)) + ' s (N/fs)' )
    print( 'Time clearance: ' + str( round(N/(4.0*fs), 2) ) )
    print( 'System_type:    ' + system_type )
    print()
    return


def plot_FRDs( freq, curves, title='Freq. response', png_fname='', figure=100 ):
    """ Plots multi FRD curves
        freq:       The freq vector
        curves:     A list of curves dictionaries: {magdB:, color:, label:}
        png_fname:  A figure .png filename to be saved on disk
        figure:     By calling a figure number, you can interleave the curves
                    in the desired figure.
    """

    # If this is a new figure, lets create it with a new axes:
    if figure not in plt.get_fignums():
        fig_frds = plt.figure(figure)
        ax = fig_frds.add_subplot()

        # plot warning level lines
        ax.plot(freq, full(freq.shape, clipWarning), label='',
                    linestyle='--', linewidth=0.5,  color='purple')

        ax.plot(freq, full(freq.shape, 0.0),         label='',
                    linestyle='--',       linewidth=0.75, color='purple')

        # formatting
        ax.set_title(title)
        ax.set_xlim(20, 20000)
        ax.set_ylim( yplotmax - yplotspan, yplotmax )
        # Y ticks in 6 dB steps
        ax.set_yticks( range(yplotmax - yplotspan, yplotmax + 6, 6) )
        ax.set_xlabel('frequency [Hz]')
        ax.set_ylabel('dB')
        ax.grid(True, which="both")

    # If the figure already exists, simply select it and select the existing axes:
    else:
        fig_frds = plt.figure(figure)
        ax = plt.gca()

    # plot curves
    for i, c in enumerate(curves):
        print(f'(LS.plotFRDs) figure#{figure} curve #{i} \'{c["label"]}\'')
        ax.semilogx( freq, c['magdB'], color=c['color'], label=c['label'] )

    # updating legend
    ax.legend()

    if png_fname:
        plt.savefig(png_fname)


def plot_system_response():
    """ plot layout:

                [recorded_waveforms]  [time_clearance]  1/3 height

                [        frequency____response       ]  2/3
    """

    fig_system_response = plt.figure('system response', figsize=(9.0, 9.0))  # in inches

    #axDUT = plt.subplot2grid(shape=(3, 2), loc=(0, 0))
    #axTCL = plt.subplot2grid(shape=(3, 2), loc=(0, 1))
    #axFRE = plt.subplot2grid(shape=(3, 2), loc=(1, 0), colspan=2, rowspan=2)
    axDUT = plt.subplot2grid(shape=(2, 2), loc=(0, 0))
    axTCL = plt.subplot2grid(shape=(2, 2), loc=(0, 1))
    axFRE = plt.subplot2grid(shape=(2, 2), loc=(1, 0), colspan=2)

    #--- time domain vectors
    vSamples = arange(0,N)                  # samples vector
    vTimes   = vSamples / float(fs)         # samples to time conversion

    #--- DUT and REFERENCE LOOP time domain plot
    axREF = axDUT.twinx()

    # Safe amplitudes
    for axtmp in (axDUT, axREF):
        for a in (-0.5, +0.5):
            axtmp.plot(vTimes, full(vTimes.shape,  a), label='',
                       linestyle='dashed', linewidth=0.5, color='gray')
        for a in (-1.0, +1.0):
            axtmp.plot(vTimes, full(vTimes.shape,  a), label='',
                       linestyle='dashed', linewidth=0.5, color='maroon')

    # DUT waveform
    axDUT.plot(vTimes, dut, 'blue', linewidth=0.5, label='DUT')

    # REF waveform
    axREF.plot(vTimes, ref, 'grey', linewidth=0.5, label='REF')

    axDUT.grid()
    axDUT.set_ylim(-3.5, 1.5)
    axDUT.set_yticks([-1, -.5, 0 , .5, 1])
    axREF.set_ylim(-1.5, 3.5)               # Sliding the dut and ref Y scales
    axREF.set_yticks([-1, -.5, 0 , .5, 1])
    axDUT.legend(loc='upper left')
    axREF.legend(loc='lower left')
    axDUT.set_xlabel('time [s]')
    axDUT.set_title('Recorded sweeps')

    #--- X cross correlation (Time Clearance)
    t  = vTimes
    t -= N/2.0 / fs                         # Centering the X ideal peak at 0 ms
    maxX = max(abs(X))
    ylim = 1000                             # Expected X >~ 1000
    if maxX > ylim:
        ylim += ylim * (maxX // ylim)
    axTCL.set_ylim(-ylim, +ylim)
    axTCL.plot(t, X, color="black", label='xcorr pb/rec')
    axTCL.grid()
    axTCL.legend()
    axTCL.set_xlabel('time (s)')
    axTCL.set_title(f'Time Clearance:\nrecorder lags  player <---o---> ' \
                    f'recorder leads player', fontsize='medium')

    # A warning text box
    msg = ''
    if maxX < 200:
        msg = 'bad spike shape'
    elif maxX < 500:
        msg = 'poor spike shape'
    if msg:
        # (these are matplotlib.patch.Patch properties)
        props = dict(boxstyle='round', facecolor='silver', alpha=0.3)
        axTCL.text( 0.0, -250.0,
                 msg,
                 bbox=props)

    #--- Freq Response graph
    F, dut_mag = DUT_FRD
    _, ref_mag = REF_FRD

    # plot warning level lines
    axFRE.plot(F, full(F.shape, clipWarning), label='',
                linestyle=':', linewidth=1.5,  color='purple')
    axFRE.plot(F, full(F.shape, 0.0),         label='',
                linestyle=':', linewidth=2.0,  color='purple')

    # plot curves
    axFRE.semilogx( F, dut_mag, color='blue', label='DUT' )
    axFRE.semilogx( F, ref_mag, color='gray', label='REF' )

    # formatting
    tmp = '' if not using_mic_response else ' (mic corrected)'
    axFRE.set_title(f'Freq. response{tmp}')
    axFRE.set_xlim(20, 20000)
    axFRE.set_ylim( yplotmax - yplotspan, yplotmax )
    # Y ticks in 6 dB steps
    axFRE.set_yticks( range(yplotmax - yplotspan, yplotmax + 6, 6) )
    axFRE.grid(True, which="both")
    axFRE.set_xlabel('frequency [Hz]')
    axFRE.set_ylabel('dB')
    # nice engineering formatting "1 K"
    axFRE.xaxis.set_major_formatter( EngFormatter() )
    axFRE.xaxis.set_minor_formatter( EngFormatter() )
    # rotate_labels for both major and minor xticks
    for label in axFRE.get_xticklabels(which='both'):
        label.set_rotation(70)
        label.set_horizontalalignment('center')
    # updating legend
    axFRE.legend()

    plt.tight_layout()
    plt.savefig(f'{png_folder}/sweep_response.png')
    print( "--- Plotting sweep system response graphs..." )


def plot_aux_graphs():
    """ Aux graphs (currently only for the prepared sweep plot)
    """

    vSamples = arange(0,N)                  # samples vector
    vTimes   = vSamples / float(fs)         # samples to time conversion

    # ---- Sweep
    fig_aux, axSWE = plt.subplots(figsize=(4.5, 2.6))  # in inches
    axSWE.plot(vTimes, sweep, '--', color='black', linewidth=2,  label='raw sweep')
    axSWE.grid()
    axSWE.plot(vTimes, tapsweep, color='blue', linewidth=1, label='tapered sweep')
    axSWE.set_ylim(-2.5, 2.5)
    axSWE.set_xlabel('time[s]')
    axSWE.legend()
    axSWE.set_title('Prepared sweeps')
    plt.savefig(f'{png_folder}/prepared_sweeps.png')
    print( "--- Plotting aux graphs..." )


def fft_to_FRD(wholeFFT, smooth_Noct=0):

    # Frequencies
    f = linspace(0, int(fs/2), int(N/2) )

    # Taking the magnitude from the positive freqs fft part
    mag = abs( wholeFFT[0 : int(N/2)] )

    # reducing the fft linspaced spectrum into a logspaced one
    f, mag = tools.logspaced_semispectrum(f, mag, FRDpoints)

    # Smoothing
    if smooth_Noct:
        mag = smooth(f, mag, Noct=smooth_Noct)

    return (f, mag)


def prepare_sweep():
    """ prepare globals to work:
            sweep:      A raw sweep.
            tapsweep:   The sequence to be played: faded sweep + a zeroes tail
            indexf1:    Index of pre-tapper end freq in tapsweep
    """
    global sweep, tapsweep, indexf1


    # The played tapsweep (len=N) will be compund of
    # a logsweep (len=N-Npad) plus a zeros tail (len=Npad).
    Npad = int(N/4.0)
    Ns   = N - Npad                             # most of array is used for sweep ;-)

    ts   = linspace(0, Ns/float(fs), Ns)        # sweep's time points array

    #--- tapered sweep window:
    # Parameters to define a window to make a tapered sweep version,
    # fade in until f1 then fade out from f2 on:
    f_start     = 5.0                           # beginning of turnon half-Hann
    f1          = 10.0                          # end of turnon half-Hann
    f2          = 0.91 * fs / 2                 # beginning of turnoff half-Hann
    f_stop      = fs/2.0                        # end of turnoff half-Hann
    Ts          = Ns/float(fs)                  # sweep duration. Lenght N-Npad samples.
    Ls          = Ts / log(f_stop/f_start)      # time for frequency to increase by factor e

    indexf1 = int(round(fs * Ls * log(f1/f_start) ) + 1) # end of starting taper
    indexf2 = int(round(fs * Ls * log(f2/f_start) ) + 1) # beginning of ending taper

    print( "--- Calculating logsweep from ", int(f_start), "to", int(f_stop), "Hz" )
    sweep       = zeros(N)                      # initialize
    sweep[0:Ns] = sin( 2*pi * f_start * Ls * (exp(ts/Ls) - 1) )
    #
    #  /\/\/\/\/\/\/\/\----  this is the LOGSWEEP + Npad, with total lenght N.

    window   = ones(N)
    # pre-taper
    window[0:indexf1]  = 0.5 * (1 - cos(pi * arange(0, indexf1)    / indexf1     ) )
    # post-taper
    window[indexf2:Ns] = 0.5 * (1 + cos(pi * arange(0, Ns-indexf2) / (Ns-indexf2)) )
    window[Ns:N]       = 0      # Zeropad end of sweep

    # Here the LOGSWEEP tapered at each end for output to DAC
    tapsweep = window * sweep

    # pending to find out the meaning fo this:
    print( f'f_start * Ls: {str(round(f_start*Ls, 2))}  Ls: {str(round(Ls,2))}')

    print( 'Finished sweep generation...\n' )


def get_offset_xcorr(sweep, dut, ref):
    """
    Determines CLEARANCE based on the offset found between recorded and played signals.
    The offset is estimated by using crosscorrelation within them.

    If the offset exceeds the ending silence (Npad zeros), then information will be lost
    and CLEARANCE warning appears.

    returns: offset, TimeClearanceOK

    """

    global X  # global scoped for plotting later

    ### Matlab code:
    # lags = N/2                    % large enough to catch most delays
    #                                 (!) no usable en Numpy.correlate
    ## if max(ref) < 0.1*max(dut)   % automatic reference selection
    ##    X=xcorr(sweep,dut,lags);  % in case reference is low, use data itself
    ##else
    ##    X=xcorr(sweep,ref,lags);  % this uses recorded reference
    ##end
    ## [~,nmax]=max(abs(X));

    # Correlate with an automatic reference selection:
    # (i) For offset estimation, it is preferred to take an undisturbed signal.
    #     The mic captured signal maybe too noisy to be able to be correlated.
    #     If not enough signal in ref channel, will use the mic channel instead.

    myref = ref
    if max(ref) < 0.1 * max(dut):  # but if no signal on ref, use data itself
        myref = dut
        print('(!) Bad level on REF ch, using DUT ch itself to estimate clearance')

    print( '--- Determining record/play delay using crosscorrelation '
           '(can take a while ...)' )

    timestamp = time()

    ### (i) scipy.signal.correlate doesn't use the parameter 'lags' as in Matlab
    #      (numpy.correlate is too slow, will use scipy.signal equivalent)

    X = signal_correlate(sweep, myref, mode="same")
    offset = int(N/2) - argmax(X)

    print( "Computed in " + str( round(time() - timestamp, 1) ) + " s" )

    print( 'Record offset: ' +  str(offset) + ' samples' + \
          ' (' +  str( round( offset/float(fs), 3) ) + ' s)' )
    if offset < 0:
        print( '(i) Negative offset means player lags recorder!' )

    Npad=int(N/4.0)
    if abs(offset) > Npad:
        TimeClearanceOK = False
    else:
        TimeClearanceOK = True

    return offset, TimeClearanceOK


def do_meas(plot_mic=False):
    """
    Compute globals about DUT Device-Under-Test and REFerence measurements.

        dut,    ref             Time domain captured waveforms

        DUT_TF, REF_TF          Freq domain Transfer Functions (whole complex FFTs)

        DUT_FRD, REF_FRD        Freq Response Data rendered over the configured
                                <FRDpoints> frequency logspaced points.
                                These are given as tuples (freq, mag)

        TimeClearanceOK         Boolean about the detected time clearance

    """

    global dut, ref, mic_response
    global DUT_TF, REF_TF
    global DUT_FRD, REF_FRD
    global TimeClearanceOK

    #---------------------------------------------------------------------------
    # ---- SPL calibration as per system type
    #---------------------------------------------------------------------------
    if system_type == 'acoustic':
        CF = Vw / (power_amp_gain * mic_cal * mic_preamp_gain * Po)
    elif system_type == 'electronic':
        CF = 1 / electronic_gain
    elif system_type == 'level-dependent':
        CF = 1 / (sig_frac * mic_cal * mic_preamp_gain * Po)
    else:
        print( "(!) Please check system_type for CF" )
        return zeros(N)

    #---------------------------------------------------------------------------
    #---------- 2. data gathering: send out sweep, record system output --------
    #---------------------------------------------------------------------------

    # Prepare test signal array
    input_channels = get_avail_input_channels()
    if  input_channels == 1:
        testSignal = array([sig_frac * tapsweep])                       # [ch0]
    else:
        # Antiphased signals on channels avoids codec midtap modulation.
        # 'sig_frac' means the applied attenuation
        testSignal = array([sig_frac * tapsweep, sig_frac * -tapsweep]) # [ch0, ch1]

    print( '--- Starting recording ...' )
    print( '(i) Some sound cards act strangely. Check carefully!' )

    # Setting sound device interface
    sd.default.samplerate = fs
    sd.default.channels = input_channels
    rec_dev_name = sd.query_devices(sd.default.device[0], kind='input' )['name']
    pbk_dev_name = sd.query_devices(sd.default.device[1], kind='output')['name']

    print(f'{Fmt.BLUE}    in:  {rec_dev_name}')
    print(f'    out: {pbk_dev_name}')
    print(f'    fs: {sd.default.samplerate} {Fmt.BOLD}CHANNELS: {input_channels}{Fmt.END}' )

    # Full duplex Play/Rec
    # (i) .transpose because the player needs an array having a column per channel.
    #     'blocking' waits to finish.
    z = sd.playrec(testSignal.transpose(), channels=input_channels, blocking=True)
    dut = z[:, 0]                               # DUT --> LEFT CHANNEL
    if  input_channels == 1:
        ref = (0.5 * sig_frac * tapsweep).transpose()
    else:
        ref = z[:, 1]                           # REF --> RIGHT CHANNEL

    #N = len(dut)   # This seems to be redundant ¿?
    print( 'Finished recording.' )

    #-------------  Checking time domain SAMPLES RECORDING LEVELS -------------
    print( "--- Checking time domain SAMPLES RECORDING LEVELS:" )
    maxdBFS_dut = 20 * log10( max( abs( dut ) ) )
    maxdBFS_ref = 20 * log10( max( abs( ref ) ) )
    # LSB: Less Significant Bit
    dut_RMS_LSBs = round(sqrt( 2**30 * sum(dut**2) / N ), 2)
    ref_RMS_LSBs = round(sqrt( 2**30 * sum(ref**2) / N ), 2)

    alert_dut = '           '
    if maxdBFS_dut >= clipWarning:
        alert_dut = 'WARNING (!)'
    alert_ref = '           '
    if maxdBFS_ref >= clipWarning:
        alert_ref = 'WARNING (!)'

    print( f'DUT channel max level: {round(maxdBFS_dut, 1):6} dBFS {alert_dut} RMS_LSBs: {dut_RMS_LSBs}')
    print( f'REF channel max level: {round(maxdBFS_ref, 1):6} dBFS {alert_ref} RMS_LSBs: {ref_RMS_LSBs}')

    #---------------------------------------------------------------------------
    #------------- 3. Determine if time clearance: -----------------------------
    # Checks if ound card play/rec delay is lower than the zeropad silence
    # at the signal end. Will use crosscorrelation
    #---------------------------------------------------------------------------
    offset = 0              # ideal record/play delay
    TimeClearanceOK = True
    if checkClearence:
        offset, TimeClearanceOK = get_offset_xcorr(sweep=sweep, dut=dut, ref=ref)

    #---------------------------------------------------------------------------
    #-------------- 4. Calculate TFs using Frequency Domain Ratios (*) ---------
    #                   UCASE used for freq domain variables.
    #                   All frequency variables are meant to be voltage spectra
    #---------------------------------------------------------------------------
    lwindo = ones(N)
    # LF pre-taper
    lwindo[0:indexf1] = 0.5 * ( 1 - cos ( pi * arange(0,indexf1) / indexf1 ) )
    lwindosweep = lwindo * sweep
    # remove play-record delay by shifting computer sweep array:
    #%sweep=circshift(sweep,-offset);            # commented out in original code
    #lwindosweep=circshift(lwindosweep,-offset); # then replaced by this line
    lwindosweep = roll(lwindosweep, -offset)

    # FFT: from time domain (lcase) to freq domain (UCASE)
    LWINDOSWEEP = S_dac * fft.fft(lwindosweep) * sig_frac   # sig_frac ~ atten
    REF         = S_adc * fft.fft(ref)
    DUT         = S_adc * fft.fft(dut)         * CF         # Calibration Factor

    # The DECONVOLUTION (i.e ~ freq domain division) provides the TF of DUT
    # (*) Above referred as 'Frequency Domain Ratios'
    DUT_TF   = DUT / LWINDOSWEEP
    REF_TF   = REF / LWINDOSWEEP

    # The original code Logsweep1quasi.m continues finding the loudspeaker
    # quasi-anechoic response, by using markers to windowing the recorded
    # time domain signal.
    # Here we don't need that, because we use the stationary in-room
    # loudspeaker response.

    # Getting a smoothed FRD (freq response data) from the measured TFs (fft)
    DUT_FRD = fft_to_FRD(DUT_TF, smooth_Noct=Noct)
    REF_FRD = fft_to_FRD(REF_TF, smooth_Noct=Noct)

    # Converting magnitudes to dB
    dut_freq, dut_mag = DUT_FRD
    ref_freq, ref_mag = REF_FRD
    DUT_FRD = (dut_freq, 20 * log10(dut_mag))
    REF_FRD = (ref_freq, 20 * log10(ref_mag))

    # Our default flat mic response has 0.0 dB values
    if using_mic_response:
        DUT_FRD = get_mic_corrected_response(DUT_FRD, plot_mic)
    else:
        print(f'{Fmt.GRAY}(do_meas) * NO * MIC correction{Fmt.END}')

    # ** END **
    # (i) The results are available in the global scope variables referenced above.


#-------------------------------------------------------------------------------
#--------------------------------- MAIN PROGRAM --------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

    # Reading command line options
    opcs_OK = True
    bad_options = ''

    for opc in sys.argv[1:]:

        if "-h" in opc.lower():
            print( __doc__ )
            print( "    SYSTEM SOUND DEVICES:\n" )
            print( sd.query_devices() )
            print( )
            sys.exit()

        elif "-noinfo" in opc.lower():
            printInfo = True

        elif "-nosmoo" in opc.lower():
            Noct = 0

        elif "-noclear" in opc.lower():
            checkClearence = False

        elif opc.lower() == "-sc":
            select_card = True

        elif "-dev" in opc.lower():
            try:
                selected_card = opc.split("=")[1]
                if not selected_card:
                    print( __doc__ )
                    sys.exit()
            except:
                print( __doc__ )
                sys.exit()

        elif "-e" in opc:
            N = 2**int(opc[2:])

        elif "-mic=" in opc:
            mic_response_path = opc.split("=")[1]

        elif "-aux" in opc.lower():
            aux_plot = True

        else:
            bad_options += opc + ' '
            opcs_OK = False

    if not opcs_OK:
        print( __doc__ )
        print(f'{Fmt.RED}Unknown command line options:{Fmt.END} {bad_options}')
        sys.exit()

    sd.default.channels     = 2
    sd.default.samplerate   = float(fs)

    if selected_card:
        i = selected_card.split(",")[0].strip()
        o = selected_card.split(",")[1].strip()
        try:    fs = int(selected_card.split(",")[2].strip())
        except: pass
        if i.isdigit(): i = int(i)
        if o.isdigit(): o = int(o)
        # A sound card failure will end the script.
        if not test_soundcard(i=i, o=o):
            sys.exit()

    if select_card:
        if not choose_soundcard():
            print( "(!) Error using devices to play/rec:" )
            for dev in sd.default.device:
                print( "    " + sd.query_devices(dev)['name'] )
            sys.exit()

    if printInfo:
        do_print_info()

    # Do create the needed raw and tapered sweeps
    prepare_sweep()

    # Prepare MIC response if a given mic response file
    if mic_response_path:
        set_mic_response()

    # MEASURE
    do_meas(plot_mic=True)

    # Checking TIME CLEARANCE
    if not TimeClearanceOK:
        print( '****************************************' )
        print( '********  POOR TIME CLEARANCE!  ********' )
        print( '********   check sweep length   ********' )
        print( '****************************************' )

    # Checking FREQ DOMAIN SPECTRUM LEVEL
    _, dut_mag = DUT_FRD
    maxdB = max( dut_mag )

    if  maxdB > 0.0:
        print( '****************************************' )
        print(f'CLIPPING DETECTED: +{round(maxdB,1)} dB  ' )
        print( '****************************************' )
    elif  maxdB > clipWarning:
        print( '****************************************' )
        print(f'CLOSE TO CLIPPING: {round(maxdB,1)} dB  ' )
        print( '****************************************' )
    elif maxdB < -20.0:
        print( '****************************************' )
        print(f'TOO LOW: {round(maxdB,1)} dB  ' )
        print( '****************************************' )
    else:
        print( '****************************************' )
        print(f'LEVEL OK: {round(maxdB,1)} dB  ' )
        print( '****************************************' )

    if do_plot:

        plot_system_response()

        if aux_plot:
            plot_aux_graphs()

        # makes the figure active (raised to foreground)
        if using_mic_response:
            plt.figure('MIC correction')

        plt.show()
