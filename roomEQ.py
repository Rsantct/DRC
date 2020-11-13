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

    Calculates a room equalizer FIR from a given in-room response, usually an
    averaged one as the provided from 'roommeasure.py'.

    Usage:

        roomEQ.py response.frd  [ options ]

            -name=      A meaningful suffix to name the output FIR file
                        (default current folder name)

            -fs=        Output FIR sampling freq (default 48000 Hz)

            -e=         Exponent 2^XX for FIR length in taps.
                        (default 15, i.e. 2^15=32 Ktaps)

            -ref=       Reference level in dB (default autodetected)

            -schro=     Schroeder freq. (default 200 Hz)

            -wFc=       Gaussian window to limit positive EQ: center freq
                        (default 1000 Hz)

            -wOct=      Gaussian window to limit positive EQ: wide in octaves
                        (default 10 octaves 20 ~ 20 KHz)

            -noPos      Does not allow positive gains at all

            -doFIR      Generates the pcm FIR after estimating the final EQ.


    NOTE:   this tool depends on github.com/AudioHumLab/audiotools

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


##########################################################################
### pyplot settings
##########################################################################
plt.rcParams.update({'font.size': 8})
fig, ax = plt.subplots( figsize=(9, 4.5) )    # in inches wide aspect
ax.set_xscale('log')
ax.grid(True, which='both', axis='x')
ax.grid(True, which='major', axis='y')
ax.set_xlim(20, 20000)
ax.set_yticks( range(-90, 60, 6) )
ax.set_ylim(-30, 18)


##########################################################################
### DEFAULTS:
##########################################################################

# Just calculates EQ, do not generates FIR
doFIR  = False

# For developers, aux plots about managing curves
dev = False

# Output:
m       = 2**15     # FIR length
fs      = 48000     # FIR fs
viewFIRs = False

# Reference level:
autoRef = True
f1, f2  = 500, 2000 # Range of freqs to get the ref level

# TARGET over the original given .frd
Noct    = 96        # Initial fine smoothing 1/96 oct.
fSchro  = 200       # Schroeder freq.
octSch  = 2         # Octaves referred to Schroeder to initiate the transition
                    # from fine smoothing towards a wider one 1/1 oct.
Tspeed  = "medium"  # Transition speed for audiotools/smoothSpectrum.py

# Gaussian window to limit positive gains:
wFc     = 1000      # center freq
wOct    = 10        # wide in octaves
noPos   = False     # avoids positive gains

# Suffix to name .pcm files
suffix = ''


##########################################################################
# 0. READING COMMAND LINE OPTIONS
##########################################################################

if len(sys.argv) == 1:
    print(__doc__)
    sys.exit()

for opc in sys.argv[1:]:

    if opc[0] != '-' and opc[-4:] in ('.frd','.txt'):
        FRDname = opc
        # Reading the FRD file
        FR, fs_FRD = tools.readFRD(FRDname)
        freq = FR[:, 0]     # >>>> frequencies vector <<<<
        mag  = FR[:, 1]     # >>>> magnitudes vector  <<<<

    elif opc[:4] == '-fs=':
        if opc[4:] in ('44100', '48000', '96000'):
            fs = int(opc[4:])
        else:
            print( "fs debe ser 44100 | 48000 | 96000" )
            sys.exit()

    elif opc[:3] == '-e=':
        if opc[3:] in ('12', '13', '14', '15', '16'):
            m = 2**int(opc[3:])
        else:
            print( "m: 12...16 (4K...64K taps)" )
            sys.exit()

    elif opc[:5] == '-ref=':
        try:
            ref_level = opc[5:]
            ref_level = round( float(ref_level), 1)
            autoRef = False
        except:
            print( __doc__ )
            sys.exit()

    elif '-sch' in opc:
        try:
            fSchro = float(opc.split('=')[-1])
        except:
            print( __doc__ )
            sys.exit()

    elif opc[:5].lower() == '-wfc=':
        try:
            wFc = float(opc[5:])
        except:
            print( __doc__ )
            sys.exit()

    elif opc[:6].lower() == '-woct=':
        try:
            wOct = float(opc[6:])
        except:
            print( __doc__ )
            sys.exit()

    elif '-nopos' in opc.lower():
        noPos = True

    elif '-v' in opc:
        viewFIRs = True

    elif '-dofir' in opc.lower():
        doFIR = True

    elif '-dev' in opc:
        dev = True

    elif opc[:6].lower() == '-name=':
        suffix = opc[6:]

    else:
        print( __doc__ )
        sys.exit()

# Aux to managing output filenames and printouts
FRDbasename = FRDname.split("/")[-1]
FRDpathname = "/".join(FRDname.split("/")[:-1])
if not suffix:
    suffix = os.path.basename(os.path.dirname(FRDname))
if not suffix:
    import pathlib
    suffix = os.path.basename(pathlib.Path().absolute())

# fs information
if fs == fs_FRD:
    print( "(i) fs=" + str(fs) + " same as enclosed in " + FRDbasename )
else:
    print( "(i) fs=" + str(fs) +  " differs from " + str(fs_FRD) + " in " + FRDbasename )

# Resolution information
print( "(i) read bins:", len(freq), ", FIR bins:", int(m/2) )
res_minphaFIR = round(fs / m, 2)
res_FRD       = round((fs / 2) / len(freq), 2)
if (m) / (2 * len(freq)) > 1:
    print( f'(!!!) minphase FIR resolution {res_minphaFIR} Hz EXCEEDS '
           f'the {res_FRD} Hz resolution from {FRDbasename}'            )
    oversampled = True
else:
    oversampled = False

#######################################################################################
# 1. TARGET CALCULATION: a smoothed version of the given freq response
#######################################################################################

# 1.1 Reference level
# 'rmag' is a heavily smoothed curve 1/1oct useful to getting the ref level
rmag = smooth(freq, mag, Noct=1)
if autoRef:
    f1_idx = (np.abs(freq - f1)).argmin()
    f2_idx = (np.abs(freq - f2)).argmin()
    # 'r2mag' is a portion of the magnitudes within the reference range:
    r2mag = rmag[ f1_idx : f2_idx ]
    # Aux ponderation array to calculate the average, same length as 'r2mag'
    weightslograte = .5
    weights = np.logspace( np.log(1), np.log(weightslograte), len(r2mag) )
    # Calculate the reference level
    ref_level = round( np.average( r2mag, weights=weights ), 2)
    print( "(i) estimated ref level: " +  str(ref_level) + " dB --> 0 dB" )
else:
    print( "(i) given ref level:     " +  str(ref_level) + " dB --> 0 dB" )

# 1.2 'target' curve: a smoothed version of the given freq response
# 'f0': the bottom freq to begin increasing smoothing towards 1/1 oct at Nyquist
f0 = 2**(-octSch) * fSchro

# 'Noct': starting fine somoothing in low freq (def 1/48 oct)
# 'Tspeed': smoothing transition speed (audiotools/smoothSpectrum.py)
print( "(i) Smoothing response for target calculation ..." )
target = smooth(freq, mag, Noct, f0=f0, Tspeed=Tspeed)

# 1.3 Move curves to ref level
mag    -= ref_level   # original curve
rmag   -= ref_level   # the 1/1 oct version
target -= ref_level   # the final target to be equalised


##########################################################################
# 2. COMPUTING THE EQ
##########################################################################

# Find the first eq curve by simply inverting:
eq  = -target

# Positive and negative hemispheres
eqPos = np.clip(eq, a_min=0,    a_max=None)
eqNeg = np.clip(eq, a_min=None, a_max=0)

# Ponderation window for positive gains
wPos = tools.logspaced_gauss(fc=wFc, wideOct=wOct, freq=freq)

# Applying the window to positive gains (noPos deactivates positive gains)
if noPos:
    eqPos.fill( 0.0 )
else:
    eqPos *= wPos

# Joining hemispheres to have an updated 'eq' curve with limited positive gains
eq = eqPos + eqNeg
eq = smooth(freq, eq, Noct=24)


##########################################################################
# 3. The output FIR to be used in a convolver.
#    freq domain ---( IFFT )---> tieme domain
##########################################################################

##########################################################################
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
##########################################################################
print( "(i) Interpolating spectrum with m = " + tools.Ktaps(m) + " @ " + str(fs) + " Hz" )
newFreq, newEq = pydsd.lininterp(freq, eq, m, fs)

# 3.2 Check for ODD length
if len(newEq) % 2 == 0:
    raise ValueError("(!) Something is wrong it must be an ODD spectrum: " + str(len(newEq)))
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


##########################################################################
# 4. MAKE PLOTS
##########################################################################

# auxiliary EQ plots ( -dev )
if dev:

    ax.axvline(fSchro, label='Schroeder', color='black', linestyle=':')

    ax.axvline (f0, label='f0 = -' + str(octSch) + ' oct vs Schroeder',
                    color='orange', linestyle=':', linewidth=1)

    ax.plot(freq, eqaux,
                 label='eqaux', linestyle=':', color='purple')

# raw response curve:
ax.plot(freq, mag,
                        label=f'FRD ({str(len(mag))} bins)',
                        color='grey', linestyle=':', linewidth=.5)

# target (smoothed) curve:
ax.plot(freq, target,
                        label='FRD smoothed',
                        color='blue', linestyle='-')

# the chunk curve used for getting the ref level:
if autoRef:
    ax.plot(freq[ f1_idx : f2_idx], rmag[ f1_idx : f2_idx ],
                        label='range to estimate ref level',
                        color='black', linestyle='--', linewidth=2)

# window for positive gains
if not noPos:
    ax.plot(freq, wPos*10, label='positive eq unitary window',
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

title = f'{FRDbasename}'
title += f'\n(ref. level @ {str(ref_level)} dB --> 0 dB)'
if oversampled:
    # these are matplotlib.patch.Patch properties
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax.text(1000.0, -27.0, '(i) FIR length oversamples FRD bins', bbox=props)

# nice engineering formatting "1 K"
ax.xaxis.set_major_formatter( EngFormatter() )
ax.xaxis.set_minor_formatter( EngFormatter() )

# rotate_labels for both major and minor xticks
for label in ax.get_xticklabels(which='both'):
    label.set_rotation(70)
    label.set_horizontalalignment('center')

ax.legend()

plt.title(title)


##########################################################################
# 5. Saving graphs to PDF:
##########################################################################
#pdfName = FRDname.replace('.frd', '_eq.pdf').replace('.txt', '_eq.pdf')
#print( "\n(i) Saving graph to file " + pdfName )
# avoid warnings from pdf
# C:\Python27\lib\site-packages\matplotlib\figure.py:1742: UserWarning:
# This figure includes Axes that are not compatible with tight_layout, so
# its results might be incorrect.
#import warnings
#warnings.filterwarnings("ignore")
#fig.savefig(pdfName, bbox_inches='tight')

##########################################################################
# 6. Saving impulse to .pcm files
##########################################################################
if not doFIR:
    print( "(i) Skeeping FIR generation. Bye!" )
    sys.exit()

# Do separate the outputs FIR in a meaningful folder (fs and taps length)

if FRDpathname:
    dirSal = f'{FRDpathname}/{str(fs)}_{tools.Ktaps(m).replace(" ","")}'
else:
    dirSal = f'{str(fs)}_{tools.Ktaps(m).replace(" ","")}'
os.system("mkdir -p " + dirSal)

# Channel Id when naming the .pcm file
ch = 'C'
if FRDbasename[0].upper() in ('L','R'):
    ch = FRDbasename[0].upper()
EQpcmname = f'{dirSal}/drc.{ch}.{suffix}.pcm'

# Saving FIR file:
print( "(i) Saving EQ FIR:" )
print( "    " + str(fs) + "_" + tools.Ktaps(m).replace(' ','') + "/" + EQpcmname.split("/")[-1] )
tools.savePCM32(imp, EQpcmname)


##########################################################################
# 7. SHOW PLOTS
##########################################################################
plt.show()


##########################################################################
# 8. FIR visualizer
##########################################################################
if viewFIRs:
    print( "FIR plotting with audiotools/IR_tool.py ..." )
    os.system("IRs_tool.py '" + EQpcmname + "' '" +
              + "' 20-20000 -dBrange=36 -dBtop=12 -1 " + str(int(fs)))

# ALL DONE ;-)
