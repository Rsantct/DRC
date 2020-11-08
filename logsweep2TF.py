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

    Computa la TF Transfer Function de un DUT (device under test) mediante
    la deconvolución de una señal de excitación (logsweep) y
    la respuesta capturada por el micrófono.

    DUT   ---> LEFT CHANNEL  (Señal del micrófono)
    LOOP  ---> RIGHT CHANNEL (Bucle opcional para ayudar a validar la medida según la
                              latencia HW vs la longitud N de la secuencia de pruebas)

    Uso:      python logsweep2TF.py  [opciones ... ...]

    -h                  Ayuda

    -sc                 Solicita una sound card y la prueba.
    -dev=cap,pbk,fs     Usa los sound devices y la fs indicada.
                        NO son devices ALSA, usar -h para ver un listado.

    -eXX                Potencia de 2 que determina la longitud=2^XX total
                        en muestras (N) de la señal de prueba. Por defecto 2^17.

    -noclearance        Elude la validación por excesiva latencia.
    -auxplots           Muestra las gráficas auxiliares (sweeps grabados)
    -notfplot           No muestra la gráfica de la TF obtenida
    -smooth             Muestra la TF suavizada

"""
#-------------------------------------------------------------------------------------------
#-------------------------------- CRÉDITOS: ------------------------------------------------
#-------------------------------------------------------------------------------------------
# Este script está basado en el siguiente código Matlab Open Source:
# 'An Open-Source Electroacoustic Measurement System'
# Richard Mann and John Vanderkooy, March 2017, Audio Research Group, University of Waterloo
#
# Publicado en:
# https://linearaudio.net/volumes/2282
# https://linearaudio.net/downloads
# https://linearaudio.net/sites/linearaudio.net/files/vol%2013%20rm%26jvdk%20readme%26m-files%20p1.zip
# https://linearaudio.net/sites/linearaudio.net/files/vol%2013%20rm%26jvdk%20readme%26m-files%20p2.zip
#
#
#   Observaciones:
#
#   - En la sección "data gathering ... ..." una vez capturada la señal 'dut' se redefine
#   N=len(dut). Esto lo he descartado entiendo que no tiene efectos secundarios.
#
#   - El nivel max de la señal en domT no se corresponde con el max en domF,
#   confirmar si es correcto, yo creo que si.
#
#   - La opciones de calibración no se toman en cuenta aquí.

#---------------------------- IMPORTING MODULES: -------------------------
import os
import sys
from time import time       # Para evaluar el tiempo de proceso de algunos cálculos,
                            # como por ejemplo la crosscorrelation que tarda un güevo.

UHOME = os.path.expanduser("~")
sys.path.append(UHOME + "/audiotools")
from smoothSpectrum import smoothSpectrum as smooth
import tools

# https://matplotlib.org/faq/howto_faq.html#working-with-threads
import matplotlib
# Later we will be able to call matplotlib.use('Agg') to replace the regular
# display backend (e.g. 'Mac OSX') by the dummy one 'Agg' in order to avoid
# incompatibility when threading this module, e.g. when using a Tcl/Tk GUI.
import matplotlib.pyplot as plt

from numpy import *
from scipy import interpolate # para aligerar el ploteo de la TF smoothed
from scipy.signal import correlate as signal_correlate

# signal.correlate muestra un FutureWarning, lo inhibimos:
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import sounddevice as sd    # https://python-sounddevice.readthedocs.io

#-------------------------------------------------------------------------------
#----------------------------- DEFAULT OPTIONS: --------------------------------
#-------------------------------------------------------------------------------
select_card         = False
selected_card       = ''
checkClearence      = True

printInfo           = True

aux_plot            = False     # Time domain aux plotting
TF_plot             = False     # Freq domain Transfer Function plotting
TF_plot_smooth      = False     # Optional smoothed TF plotting

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

binsFRD     = 2**14             # Freq bins for output .frd files

yplotmax    = 10                # TF plots above 0 dB
yplotspan   = 60                # total scale of TF plots

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

    result = False

    dummy1sec = zeros(int(fs))

    print( 'Trying:' )

    try:
        sd.default.device = i, o
        print( f'    {sd.query_devices(i)["name"]}')
        print( f'    {sd.query_devices(o)["name"]}')
    except Exception as e:
        print( f'(!) Error accesing devices [{i},{o}]: {e}' )

    try:
        chk_rec = sd.check_input_settings (i, channels=ch, samplerate=float(fs))
        chk_pb  = sd.check_output_settings(o, channels=ch, samplerate=float(fs))
        print( f'Sound card parameters OK' )
    except Exception as e:
        print( f'(!) Sound card [{i},{o}] ERROR: {e}' )

    try:
        dummy = sd.playrec(dummy1sec, samplerate=fs, channels=ch)
        print( 'Sound device settings are supported\n' )
        result = True
    except Exception as e:
        print( f'\n(!) FAILED to playback and recording on selected device: {e}\n' )

    return  result


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
    print( 'Duration:       ' + str(round((N/float(fs)), 2)) + ' s (N/fs)' )
    print( 'Time clearance: ' + str( round(N/(4.0*fs), 2) ) )
    print( 'System_type:    ' + system_type )
    print()
    return


def do_plot_aux_graphs(png_folder=f'{UHOME}'):
    """ Aux graphs on time domain
    """

    vSamples = arange(0,N)              # samples vector
    vTimes   = vSamples / float(fs)     # samples to time conversion

    # ---- Sweep
    plt.figure(10)
    plt.plot(vTimes, sweep, '--', color='black', linewidth=2,  label='raw sweep')
    plt.grid()
    plt.plot(vTimes, tapsweep, color='blue', linewidth=1, label='tapered sweep')
    plt.ylim(-1.5, 1.5)
    plt.xlabel('time[s]')
    plt.legend()
    plt.title('Prepared sweeps')
    plt.savefig(f'{png_folder}/prepared_sweeps.png')

    #--- DUT and REFERENCE LOOP time domain plot
    fig = plt.figure(20)
    axDUT = fig.add_subplot()
    axDUT.plot(vTimes, dut, 'blue', label='DUT')
    axREF = axDUT.twinx()
    axREF.plot(vTimes, ref, 'grey', label='REF (offset+2.0)')
    axDUT.grid()
    axDUT.set_ylim(-1.5, 3.5)
    axREF.set_ylim(-3.5, 1.5)
    fig.legend()
    axDUT.set_xlabel('Time [s]')
    axDUT.set_title('Recorded sweeps')
    plt.savefig(f'{png_folder}/time_domain_recorded.png')

    #--- X cross correlation (Time Clearance)
    plt.figure(30)
    t  = vTimes
    t -= N/2.0 / fs               # centramos el 0 en el pico ideal de X
    plt.plot(t, X, color="black", label='xcorr pb/rec')
    plt.grid()
    plt.legend()
    plt.xlabel('time (s)')
    plt.title('Time Clearance:\nrecorder lags  player <----o----> recorder leads player')
    plt.savefig(f'{png_folder}/time_clearance.png')

    print( "--- Plotting Time Domain graphs..." )


def plot_FRdB( f, magdB, figure=100, label='', color='blue', title='Freq. response',
                                                         png_fname='' ):
    """ Plots a FRD freq response data given in dB

            figure      allows to perform multicurve figures
            png_fname   dumps a png image of the plotted graph
    """
    plt.figure(figure)
    plt.semilogx( f, magdB, color=color, label=label )
    plt.xlim(20, 20000)
    plt.ylim( yplotmax - yplotspan, yplotmax )
    plt.grid(True, which="both")
    plt.legend()
    plt.xlabel('frequency [Hz]')
    plt.ylabel('dB')
    plt.title(title)
    if png_fname:
        plt.savefig(png_fname)


def do_plot_TF(png_fname=f'{UHOME}/freq_response.png'):
    """ freq domain Transfer Function plotting
    """

    # REFERENCE
    f, REF_FR = fft_to_FRD(REF_TF, fs)

    plot_FRdB( f, 20 * log10(REF_FR), label='REF',
                                      color='grey',
                                      png_fname=png_fname )

    # DUT
    if not TF_plot_smooth:

        f, DUT_FR = fft_to_FRD(DUT_TF, fs)

        plot_FRdB( f, 20 * log10(DUT_FR) , label='DUT',
                                           color='blue',
                                           png_fname=png_fname )
    # or DUT smoothed
    else:

        f, DUT_FR = fft_to_FRD(DUT_TF, fs, smooth_Noct=24)

        plot_FRdB( f, 20 * log10(DUT_FR) , label='DUT 1/24 oct smooth',
                                           color='green',
                                           png_fname=png_fname )

    print( "--- Plotting Freq Response graphs..." )


def fft_to_FRD(wholeFFT, fs=fs, smooth_Noct=0, Nbins=binsFRD):
    """
        Input:

            wholeFFT        A whole FFT array
            fs              Sampling freq
            smooth_Noct     Do smooth 1/N oct the output curve
            Nbins           Number of freq bins of the output curve


        Output:

            (f, mag)        A real valued positive semi-spectrum tuple FRD data
                            (mag is given in lineal values not in dB)
    """

    N = len(wholeFFT)

    # Frequencies
    f = linspace(0, int(fs/2), int(N/2) )

    # Taking the magnitude from the positive freqs fft part
    mag = abs( wholeFFT[0:int(N/2)] )

    # interpolates to Nbins
    f, mag = tools.interp_semispectrum(f, mag, fs, Nbins)

    # Smoothing
    if smooth_Noct:
        print( '--- Smoothing spectrum (this can take a while ...)' )
        t_start = time()
        mag = smooth(f, mag, Noct=smooth_Noct)
        print(f'--- Smoothing computed in {str( round(time() - t_start, 1) )} s' )

    return f, mag


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
    Ns   = N - Npad                         # most of array is used for sweep ;-)

    ts   = linspace(0, Ns/float(fs), Ns)    # array de tiempos del sweep
    # Al sweep se le aplica una 'windo' para 'fade in/out' en f1 y f2
    f_start     = 5.0                       # beginning of turnon half-Hann
    f1          = 10.0                      # end of turnon half-Hann
    f2          = 0.91 * fs / 2             # beginning of turnoff half-Hann
    f_stop      = fs/2.0                    # end of turnoff half-Hann
    Ts          = Ns/float(fs)              # sweep duration. Lenght N-Npad samples.
    Ls          = Ts / log(f_stop/f_start)  # time for frequency to increase by factor e

    #--- tapered sweep window:
    indexf1 = int(round(fs * Ls * log(f1/f_start) ) + 1)     # end of starting taper
    indexf2 = int(round(fs * Ls * log(f2/f_start) ) + 1)     # beginning of ending taper

    print( "--- Calculating logsweep from ", int(f_start), "to", int(f_stop), "Hz" )
    sweep       = zeros(N)                  # initialize
    sweep[0:Ns] = sin( 2*pi * f_start * Ls * (exp(ts/Ls) - 1) )
    #
    #  /\/\/\/\/\/\/\/\----  this is the LOGSWEEP+Npad, total lenght N.

    # tappers para fade in / fade out en el tramo del sweep:
    windo   = ones(N)
    # pre-taper
    windo[0:indexf1]  = 0.5 * (1 - cos(pi * arange(0, indexf1)    / indexf1     ) )
    # post-taper
    windo[indexf2:Ns] = 0.5 * (1 + cos(pi * arange(0, Ns-indexf2) / (Ns-indexf2)) )
    windo[Ns:N]       = 0       # Zeropad end of sweep. (i) Esto creo que es redundante
                                # porque el sweep ya tiene zeros ahí.
    tapsweep = windo * sweep    # Here the LOGSWEEP tapered at each end for output to DAC

    # NOTA no tengo claro el interés de pritar esto:
    print( "f_start * Ls: " + str(round(f_start*Ls, 2)) + \
          "   Ls: "  + str(round(Ls,2)) + "    ¿!?" )
    print( 'Finished sweep generation...' )
    print( )


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
    # (i) Para estimar el offset, es preferible tomar una señal poco alterada.
    #     Es posible que la señal captada por el micro sea 'noisy' para poder correlarla.
    #     Si no se detecta señal en el canal de referencia, se usa a malas la del micro.
    myref = ref
    if max(ref) < 0.1 * max(dut):  # but if no signal on ref, use data itself
        myref = dut
        print( "(i) Bad level on REF ch, using DUT ch itself to estimate clearance" )

    print( "--- Determining record/play delay using crosscorrelation (can take a while ...)" )

    timestamp = time()

    ### (i) Correlation in NUMPY/SCIPY no usa el parámetro lags como en MATLAB

    # Correlate de Numpy tarda mucho, usamos el de signal
    # PEEEERO escupe un FutureWarning al menos en mi versión
    # que queda feo en la consola :-/
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


def do_meas():
    """
    Compute globals about DUT Device-Under-Test and REFerence measurements.

        dut,    ref      --> Time domain responses
        DUT_TF, REF_TF   --> Freq domain responses (whole complex FFT)
        TimeClearanceOK  --> Boolean about the detected time clearance

    """

    global dut,    ref          # Time domain recordings
    global DUT_TF, REF_TF       # FFT Freq domain
    global TimeClearanceOK      # The detected time clearance (boolean)

    #---------------------------------------------------------------------------
    # ---- Determina SPL calibration factor en función del tipo de sistema -----
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
    print( '--- Starting recording ...' )
    print( '(i) Some sound cards act strangely. Check carefully!' )
    # Antiphased signals on channels avoids codec midtap modulation.
    # Se aplica atenuación según 'sig_frac'
    stereo = array([sig_frac * tapsweep, sig_frac * -tapsweep]) # [ch0, ch1]
    sd.default.samplerate = fs
    sd.default.channels = 2
    rec_dev_name = sd.query_devices(sd.default.device[0])['name']
    pbk_dev_name = sd.query_devices(sd.default.device[1])['name']
    print(f'    in: {rec_dev_name}, out: {pbk_dev_name}, fs: {sd.default.samplerate}')
    # (i) .transpose pq el player necesita una array con cada canal en una COLUMNA.
    z = sd.playrec(stereo.transpose(), blocking=True) # 'blocking' waits to finish.
    dut = z[:, 0]   # we use LEFT  CHANNEL as DUT
    ref = z[:, 1]   # we use RIGHT CHANNEL as REFERENCE
    #N   = len(dut) # esto creo que es innecesario
    print( 'Finished recording.' )

    #-------------  Checking time domain RECORDING LEVELS ----------------------
    print( "--- Checking levels:" )
    maxdBFS_dut = 20 * log10( max( abs( dut ) ) )
    maxdBFS_ref = 20 * log10( max( abs( ref ) ) )
    # Esto supongo que debe ser una información de energía ¿?
    DUT_RMS_LSBs = round(sqrt( 2**30 * sum(dut**2) / N ), 2)
    REF_RMS_LSBs = round(sqrt( 2**30 * sum(ref**2) / N ), 2)

    if maxdBFS_dut >= clipWarning:
        print( 'DUT channel max level:', round(maxdBFS_dut, 1), 'dBFS  WARNING (!)', \
              'RMS_LSBs:',  DUT_RMS_LSBs )
    else:
        print( 'DUT channel max level:', round(maxdBFS_dut, 1), 'dBFS             ', \
              'RMS_LSBs:',  DUT_RMS_LSBs )

    if maxdBFS_ref >= clipWarning:
        print( 'REF channel max level:', round(maxdBFS_ref, 1), 'dBFS  WARNING (!)', \
              'RMS_LSBs:',  REF_RMS_LSBs )
    else:
        print( 'REF channel max level:', round(maxdBFS_ref, 1), 'dBFS             ', \
              'RMS_LSBs:',  REF_RMS_LSBs )

    #---------------------------------------------------------------------------
    #------------- 3. Determine if time clearance: -----------------------------
    # Checks if ound card play/rec delay is lower than the zeropad silence at the signal end.
    # ( Will use crosscorrelation )
    #---------------------------------------------------------------------------
    offset = 0              # ideal record/play delay
    TimeClearanceOK = True  # forzamos aunque pudiera ser falso.
    if checkClearence:
        offset, TimeClearanceOK = get_offset_xcorr(sweep=sweep, dut=dut, ref=ref)

    #---------------------------------------------------------------------------
    #-------------- 4. Calculate TFs using Frequency Domain Ratios (*) ---------
    #                   UCASE used for freq domain variables.
    #                   All frequency variables are meant to be voltage spectra
    #---------------------------------------------------------------------------
    lwindo = ones(N)
    lwindo[0:indexf1] = 0.5 * ( 1 - cos ( pi * arange(0,indexf1) / indexf1 ) ) # LF pre-taper
    lwindosweep = lwindo * sweep
    # remove play-record delay by shifting computer sweep array:
    ## %sweep=circshift(sweep,-offset);             # Esto aparece comentado en el cód. original,
    ## lwindosweep=circshift(lwindosweep,-offset);  # que usa este código.
    lwindosweep = roll(lwindosweep, -offset)

    # (i) NÓTESE que trabajamos con FFTs completas:
    LWINDOSWEEP = S_dac * fft.fft(lwindosweep) * sig_frac   # sig_frac es la atenuación establecida al sweep
    REF         = S_adc * fft.fft(ref)
    DUT         = S_adc * fft.fft(dut)         * CF         # CF calibration factor

    # (i) La DECONVOLUCIÓN ( es decir división en el dominio de la frecuencia)
    #     - (*) arriba referico como 'Frequency Domain Ratios' -
    #     proporciona la TF Transfer Function del dispositivo bajo ensayo DUT
    #     que es el objetivo que nos ocupa ;-)

    ##%TF       = DUT./SWEEP;                                # <- código original comentado
    DUT_TF   = DUT / LWINDOSWEEP  # (orig named as 'TF' )   this has good Nyquist behaviour
    REF_TF   = DUT / REF          # (orig named as 'TF2')

    # END

    # (i)   The results are the above referenced global scoped variables.
    #
    #       The orginal code Logsweep1quasi.m continues finding the loudspeaker
    #       quasi-anechoic response, by using markers to windowing the recorded
    #       time domain signal.
    #       Here we don't need that, because we use the stationary in-room
    #       loudspeaker response.


#-------------------------------------------------------------------------------
#--------------------------------- MAIN PROGRAM --------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

    # Las gráficas son mostradas por defecto
    TF_plot     = True
    aux_plot    = True

    # Lee la command line
    opcsOK = True
    for opc in sys.argv[1:]:

        if "-h" in opc.lower():
            print( __doc__ )
            print( "    SYSTEM SOUND DEVICES:\n" )
            print( sd.query_devices() )
            print( )
            sys.exit()

        elif "-noinfo" in opc.lower():
            printInfo = True

        elif "-notf" in opc.lower():
            TF_plot = False

        elif "-noaux" in opc.lower():
            aux_plot = False

        elif "-smoo" in opc.lower():
            TF_plot_smooth = True

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

        else:
            opcsOK = False

    if not opcsOK:
        print( __doc__ )
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
        if not test_soundcard(i=i, o=o):    # Si fallara sale
            sys.exit()

    if select_card:
        if not choose_soundcard():          # Si falla la selección
            print( "(!) Error using devices to play/rec:" )
            for dev in sd.default.device:
                print( "    " + sd.query_devices(dev)['name'] )
            sys.exit()

    if printInfo:
        do_print_info()

    # Do create the needed raw and tapered sweeps
    prepare_sweep()

    # MEASURE
    do_meas()

    # Checking TIME CLEARANCE
    if not TimeClearanceOK:
        print( '****************************************' )
        print( '********  POOR TIME CLEARANCE!  ********' )
        print( '********   check sweep length   ********' )
        print( '****************************************' )


    # Checking FREQ DOMAIN SPECTRUM LEVEL
    _, mag = fft_to_FRD( DUT_TF, fs, smooth_Noct=24 )

    maxdB = max( 20 * log10(mag) )

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

    if aux_plot:
        do_plot_aux_graphs()

    if TF_plot:
        do_plot_TF()

    if aux_plot or TF_plot:
        plt.show()
