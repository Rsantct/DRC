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


    NOTE:

    This tool depends on github.com/AudioHumLab/audiotools

"""
import os
import sys
import numpy as np
from scipy import signal
from scipy.interpolate import interp1d

# https://matplotlib.org/faq/howto_faq.html#working-with-threads
import matplotlib
# Later we will be able to call matplotlib.use('Agg') to replace the regular
# display backend (e.g. 'Mac OSX') by the dummy one 'Agg' in order to avoid
# incompatibility when threading this module, e.g. when using a Tcl/Tk GUI.
import matplotlib.pyplot as plt

from matplotlib.ticker import EngFormatter

### ~/audiotools
HOME = os.path.expanduser("~")
sys.path.append(HOME + "/audiotools")
import tools
import pydsd
from smoothSpectrum import smoothSpectrum as smooth


### roomEQ.py DEFAULTS:

# Just calculates EQ, do not generates FIR
doFIR  = False

# For developers, aux plots about managing curves
dev = False

# Output:
m       = 2**15     # FIR length
fs      = 48000     # FIR fs
viewFIRs = False

# Reference level:
ref_level = None
f1, f2  = 500, 2000 # Range of mid freqs to get the ref level

# TARGET over the original given .frd
Noct    = 96        # Initial fine smoothing 1/96 oct.
fSchro  = 200       # Schroeder freq.
octSch  = 2         # Octaves referred to Schroeder to initiate the transition
                    # from fine smoothing towards a wider one 1/1 oct.
Tspeed  = "medium"  # Transition speed for audiotools/smoothSpectrum.py

# Gaussian windows to limit positive gains:
wLfc    = 630       # Left window center freq (default: at 5 oct ~ 630 Hz)
wHfc    = 630       # Right window center
wLoct   = 5         # span in octaves for the left side of wL.
wHoct   = 5         # span in octaves for the right side of wH.
noPos   = False     # avoids positive gains


def main(FRDname, ax, ref_level=None):

    FRDbasename = os.path.basename(FRDname)
    FRDdirname  = os.path.dirname(FRDname)

    print( f'--- processing {FRDbasename}')

    # Retreiving channel Id for naming files
    ch = FRDbasename
    if FRDbasename[0].upper() in ('L','R','C'):
        ch = FRDbasename[0].upper()

    if not FRDdirname:
        FRDdirname = os.getcwd()

    FRDpath = f'{FRDdirname}/{FRDbasename}'

    # Reading the FRD file
    FR, fs_FRD = tools.readFRD(FRDpath)
    freq = FR[:, 0]     # >>>> frequencies vector <<<<
    mag  = FR[:, 1]     # >>>> magnitudes vector  <<<<


    ############################################################################
    # 1. TARGET CALCULATION: a smoothed version of the given freq response
    ############################################################################

    # 1.1 Reference level
    # 'rmag' is a heavily smoothed curve 1/1oct useful to getting the ref level
    rmag = smooth(freq, mag, Noct=1)
    if ref_level == None:
        f1_idx = (np.abs(freq - f1)).argmin()
        f2_idx = (np.abs(freq - f2)).argmin()
        # 'r2mag' is a portion of the magnitudes within the reference range:
        r2mag = rmag[ f1_idx : f2_idx ]
        # Aux ponderation array to calculate the average, same length as 'r2mag'
        weightslograte = .5
        weights = np.logspace( np.log(1), np.log(weightslograte), len(r2mag) )
        # Calculate the reference level
        ref_level = round( np.average( r2mag, weights=weights ), 2)
        print( f'(i) estimated ref level: {str(ref_level)} dB --> 0 dB' )
        autoRef = True
    else:
        print( f'(i) given ref level:     {str(ref_level)} dB --> 0 dB' )
        autoRef = False

    # 1.2 'target' curve: a smoothed version of the given freq response
    # 'f0': the bottom freq to begin increasing smoothing towards 1/1 oct at Nyquist
    f0 = 2**(-octSch) * fSchro

    # 'Noct': starting fine somoothing in low freq (def 1/48 oct)
    # 'Tspeed': smoothing transition speed (audiotools/smoothSpectrum.py)
    print( '(i) Smoothing response for target calculation ...' )
    target = smooth(freq, mag, Noct, f0=f0, Tspeed=Tspeed)

    # 1.3 Move curves to ref level
    mag    -= ref_level   # original curve
    rmag   -= ref_level   # the 1/1 oct version
    target -= ref_level   # the final target to be equalised


    ############################################################################
    # 2. COMPUTING THE EQ
    ############################################################################

    # Find the first eq curve by simply inverting:
    eq  = -target

    # Positive and negative hemispheres
    eqPos = np.clip(eq, a_min=0,    a_max=None)
    eqNeg = np.clip(eq, a_min=None, a_max=0)

    # Ponderation window for positive gains
    # window left side (low freqs) and right side (high freqs)
    w_Low    = tools.logspaced_gauss(fc=wLfc, wideOct=wLoct * 2, freq=freq)
    w_High   = tools.logspaced_gauss(fc=wHfc, wideOct=wHoct * 2, freq=freq)

    Lfc_idx  = len( np.where(freq < wLfc )[0] ) - 1
    Hfc_idx  = len( np.where(freq < wHfc)[0] ) - 1

    w_Low    = w_Low [ : Lfc_idx]
    w_High   = w_High[Hfc_idx : ]
    w_Mid    = np.ones( len(freq) - len(w_Low) - len(w_High) )

    w = np.concatenate( (w_Low, w_Mid, w_High) )

    # Applying the window to positive gains (noPos deactivates positive gains)
    if noPos:
        eqPos.fill( 0.0 )
    else:
        eqPos *= w

    # Joining hemispheres to have an updated 'eq' curve with limited positive gains
    eq = eqPos + eqNeg
    eq = smooth(freq, eq, Noct=24)


    ############################################################################
    # 3. The output FIR to be used in a convolver.
    #    freq domain ---( IFFT )---> tieme domain
    ############################################################################

    ############################################################################
    # 3.1 Interpolating the 'eq' curve to reach the desired 'm' length and 'fs'
    #     on the output FIR
    #
    #   The ARTA .frd files have:
    #   - a length power of 2
    #   - first bin is 0 Hz
    #   - if fs=48000, last bin is fs/2
    #   - if fs=44100, last bin is (fs/2)-1  ¿!? what the fuck
    #
    #   NOTE: when interpolating by using pydsd.lininterp it is guarantied:
    #   - The length of the new semispectrum will be ODD (power of 2) + 1,
    #     this is convenient to compute an EVEN whole spectrum, which will
    #     be used to synthethise the FIR by IFFT.
    #   - The first bin is 0 Hz and last bin is Nyquist.
    #
    ############################################################################
    print( f'(i) Interpolating spectrum with m = {tools.Ktaps(m)} @ {str(fs)} Hz' )
    newFreq, newEq = pydsd.lininterp(freq, eq, m, fs)

    # 3.2 Check for ODD length
    if len(newEq) % 2 == 0:
        raise ValueError(f'(!) ERROR, it must be an ODD spectrum: {len(newEq)}')
        sys.exit()

    # 3.3 dBs --> linear
    newEqlin = 10.0**(newEq/20.0)

    # 3.4 Impulse is computed by doing the IFFT of the 'newEq' curve.
    #     (i) 'newEq' is an abstraction reduced to the magnitudes of positive
    #         frequencies, but IFFT needs a CAUSAL spectrum (with minimum phase)
    #         also a COMPLET one (having positive and negative frequencies).
    wholespectrum = pydsd.minphsp( pydsd.wholespmp(newEqlin) ) # min-phase is addded

    # freq. domain  --> time domain and windowing
    imp = np.real( np.fft.ifft( wholespectrum ) )
    imp = pydsd.semiblackmanharris(m) * imp[:m]

    # From now on, 'imp' has a causal response, a natural one, i.e. minimum phase


    ############################################################################
    # 4. MAKE PLOTS
    ############################################################################
    ax.set_xscale('log')
    ax.grid(True, which='both', axis='x')
    ax.grid(True, which='major', axis='y')
    ax.set_xlim(20, 20000)
    ax.set_yticks( range(-90, 60, 6) )
    ax.set_ylim(-30, 18)

    # auxiliary EQ plots ( -dev )
    if dev:

        ax.axvline(fSchro, label='Schroeder', color='black', linestyle=':')

        ax.axvline (f0, label='f0 = -' + str(octSch) + ' oct vs Schroeder',
                        color='orange', linestyle=':', linewidth=1)

        ax.plot(freq, eqaux,
                     label='eqaux', linestyle=':', color='purple')

    # raw response curve:
    ax.plot(freq, mag,
                            label='FRD',
                            color='grey', linestyle=':', linewidth=.5)

    # target (smoothed) curve:
    ax.plot(freq, target,
                            label='FRD schoeder smoothed',
                            color='blue', linestyle='-')

    # the chunk curve used for getting the ref level:
    if autoRef:
        ax.plot(freq[ f1_idx : f2_idx], rmag[ f1_idx : f2_idx ],
                            label='range to estimate ref level',
                            color='black', linestyle='--', linewidth=2)

    # window for positive gains (scaled at level 10 for clarity)
    if not noPos:
        ax.plot(freq, w*10, label='positive eq unitary window',
                            color='grey', linestyle='dotted')

    # computed EQ curve:
    ax.plot(newFreq, newEq,
                            label=f'EQ FIR ({int(m/1024)} Ktaps)',
                            color='green')

    # estimated result curve:
    if dev:
        ax.plot(freq, (target + eq),
                            label='estimated result',
                            color='green', linewidth=1.5)


    # A text box with resolution info
    # (these are matplotlib.patch.Patch properties)
    props = dict(boxstyle='round', facecolor='green', alpha=0.3)
    ax.text( 4000.0, -15.0,
             f'FIR {int(m/1024)} Ktaps, freq. resol: {round(fs/m, 1)} Hz',
             bbox=props)

    # plot title
    title = f'{FRDbasename}\n(ref. level @ {str(ref_level)} dB --> 0 dB)'
    ax.set_title(title)

    # nice engineering formatting "1 K"
    ax.xaxis.set_major_formatter( EngFormatter() )
    ax.xaxis.set_minor_formatter( EngFormatter() )

    # rotate_labels for both major and minor xticks
    for label in ax.get_xticklabels(which='both'):
        label.set_rotation(70)
        label.set_horizontalalignment('center')

    ax.legend(loc='lower right')


    ############################################################################
    # 5. Saving FIR to .pcm
    ############################################################################
    if doFIR:

        # Separates the output FIR in a meaningful folder (fs and taps length)
        fir_folder = f'{FRDdirname}/{str(fs)}_{tools.Ktaps(m).replace(" ","")}'
        os.system(f'mkdir -p {fir_folder}')

        EQpcmname = f'{fir_folder}/drc.{ch}.pcm'

        # Saving FIR file:
        print( f'(i) Saving roomEQ FIR:' )
        print( f'    {EQpcmname}' )
        tools.savePCM32(imp, EQpcmname)

    else:
        print( '(i) Skiping FIR saving' )


if __name__ == '__main__':

    # reading COMMAND LINE options
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit()

    FRDnames = []

    opcsOK = True

    for opc in sys.argv[1:]:

        if opc[0] != '-' and opc[-4:] in ('.frd','.txt'):
            FRDnames.append(opc)

        elif opc[:4] == '-fs=':
            if opc[4:] in ('44100', '48000', '96000'):
                fs = int(opc[4:])
            else:
                print( "fs must be in 44100 | 48000 | 96000" )
                sys.exit()

        elif opc[:3] == '-e=':
            if opc[3:] in ('12', '13', '14', '15', '16'):
                m = 2**int(opc[3:])
            else:
                print( "m: 12...16 (4K...64K taps)" )
                sys.exit()

        elif opc[:5] == '-ref=':
            try:
                ref_level = opc.split('=')[-1]
                ref_level = round( float(ref_level), 1)
            except:
                opcsOK = False

        elif '-sch' in opc:
            try:
                fSchro = float(opc.split('=')[-1])
            except:
                opcsOK = False

        elif '-wlfc=' in opc.lower():
            try:
                wLfc = float(opc.split('=')[-1])
            except:
                opcsOK = False

        elif '-whfc=' in opc.lower():
            try:
                wHfc = float(opc.split('=')[-1])
            except:
                opcsOK = False

        elif '-wloct=' in opc.lower():
            try:
                wLoct = float(opc.split('=')[-1])
            except:
                opcsOK = False

        elif '-whoct=' in opc.lower():
            try:
                wHoct = float(opc.split('=')[-1])
            except:
                opcsOK = False

        elif '-nopos' in opc.lower():
            noPos = True

        elif '-v' in opc:
            viewFIRs = True

        elif '-dofir' in opc.lower():
            doFIR = True

        elif '-dev' in opc:
            dev = True

        else:
            print( __doc__ )
            sys.exit()

    if not opcsOK:
        print( __doc__ )
        sys.exit()



    # prepare pyplot
    plt.rcParams.update({'font.size': 8})

    # prepare subplots as per the number of given FRD files
    nrows = len(FRDnames)
    fig, axs = plt.subplots( nrows=nrows, ncols=1,
                             figsize=(9, 4.5 * nrows) ) # in inches, wide aspect

    # Processing FRDs
    # (if only one, plt.subplots will not return an array of axes)
    if len(FRDnames) == 1:
        main(FRDnames[0], axs, ref_level)

    elif len(FRDnames) > 1:
        for i, FRDname in enumerate(FRDnames):
            main(FRDname, axs[i], ref_level)

    else:
        print(__doc__)
        sys.exit()

    # Tightening plot layout
    plt.tight_layout()

    # Saving graphs by using the folder beholding the last FRD file name
    png_folder = os.path.dirname( FRDnames[-1] )
    if not png_folder:
        png_folder = os.getcwd()
    png_path = f'{png_folder}/roomEQ_drc.png'
    print( f'(i) Saving graph to file: {png_path}' )
    fig.savefig(png_path)

    # Display plots
    plt.show()

    # ...
    if viewFIRs:
        print( "FIR plotting with audiotools/IR_tool.py ..." )
        os.system("IRs_tool.py '" + EQpcmname + "' '" +
                  + "' 20-20000 -dBrange=36 -dBtop=12 -1 " + str(int(fs)))

