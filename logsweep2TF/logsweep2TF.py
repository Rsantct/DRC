#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    logsweep2TF.py v0.1

    Obtiene la TF Transfer Function de un DUT (device under test) mediante
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
#
#---------------------------- IMPORT MODULES -------------------------
#  ~/audiotools modules
import os
import sys
HOME = os.path.expanduser("~")
sys.path.append(HOME + "/audiotools")
try:
    import utils
    from smoothSpectrum import smoothSpectrum as smooth
except:
    raise ValueError("rew2fir.py necesita https://githum.com/AudioHumLab/audiotools")
    sys.exit()
# end of /audiotools modules

from time import time       # Para evaluar el tiempo de proceso de algunos cálculos,
                            # como por ejemplo la crosscorrelation que tarda un güevo.

from matplotlib import pyplot as plt
from numpy import *
from scipy import interpolate # para aligerar el ploteo de la TF smoothed

from scipy.signal import correlate as signal_correlate
# signal.correlate muestra un FutureWarning, lo inhibimos:
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import sounddevice as sd    # https://python-sounddevice.readthedocs.io

#---------------------------------------------------------------------
#------------------------- DEFAULT OPTIONS: --------------------------
#---------------------------------------------------------------------
select_card         = False
selected_card       = None
checkClearence      = True

printInfo           = True
TFplot              = False
auxPlots            = False
plotSmoothSpectrum  = False  # añadir gráfica TF suavizada (OjO esto tarda)

#---------------------------------------------------------------------
#--------------------------- DEFAULT PARAMETERS: ---------------------
#---------------------------------------------------------------------
sig_frac    = 0.5               # Fraction of full scale applied to play the sweep.
fs          = 48000             # Must ensure that sound driver accepts.
N           = 2**18             # Lenght of the total sequence, make this
                                # larger if there is insufficient time clearance
system_type = 'electronic'      # 'acoustic', 'electronic', 'level-dependent'
Po          = 2e-5              # SPL reference pressure
c           = 343               # speed of sound

#--------------------------- USE OPTIONS --------------------
dBclearance         = 10        # white space above TF plots
dBspan              = 60        # total scale of TF plots
minFrecPlot         = 10        # min freq to plot
clipWarning         = -3.0      # dBFS warning when capturing

#----------------- System calibration factor CF for dut --------------------
power_amp_gain  = 10            # V/V acoustic
mic_cal         = 0.012         # V/Pa acoustic
mic_preamp_gain = 10.0          # V/V acoustic
Vw              = 1.0           # 2.83 V/watt8ohms acoustic Leave this=1 if not wanted
electronic_gain = 1.0           # total gain in series with electronic system
#------------------- Enter value for your soundcard: ------------------------
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


#---------------------------------------------------------------------
#----------------------- INTERNAL PROCEDURES -------------------------
#---------------------------------------------------------------------

def choose_soundcard():
    #sd.default.device = 'Built-in Microphone', 'Built-in Output' # Mac Book

    tested = False
    tries = 0
    while not tested and tries < 3:
        print "\n    SYSTEM SOUND DEVICES:\n"
        print sd.query_devices()
        print
        print "    Select capture  device: "; i = int(raw_input())
        print "    Select playback device: "; o = int(raw_input())
        tested = test_soundcard(i,o)
        tries += 1

    return tested

def test_soundcard(i="default",o="default", fs=fs):

    playrecOK = False
    dummy1sec = zeros(int(1*fs))
    print "\n    SYSTEM SOUND DEVICES:\n"
    print sd.query_devices()
    print
    sd.default.device = i, o # Sets the default device for the sounddevide module.
    print "    Trying play/rec:"

    try:
        print "    ", sd.query_devices(i)['name']
        print "    ", sd.query_devices(o)['name']

    except:
        print "(!) Error accediendo a los devices " + str(i) + " / " + str(o)
        return  playrecOK

    try:
        chk_rec = sd.check_input_settings(i, channels=2, samplerate=float(fs))
        chk_pb  = sd.check_output_settings(o, channels=2, samplerate=float(fs))
        dummy = sd.playrec(dummy1sec)
        playrecOK = True
        print "    Sound device settings are supported"
    except:
        print "\n(!) FAILED to playback and recording on selected device."

    return  playrecOK

def do_print_info():

    print "--- SYSTEM SOUND DEVICES:"
    print sd.query_devices()
    rec, pb = sd.default.device
    print "    Using '" + str(rec) + "' to CAPTURE, '" + str(pb) + "' to PLAYBACK"
    print "    [ DUT ] --> LEFT  ch  ||  [ REF ] --> RIGHT ch"
    print "--- Parameters:"
    sig_frac_dBFS = round(20 * log10(sig_frac), 2)
    print 'Amplitude:      ' + str(sig_frac) + ' (' + str(sig_frac_dBFS) + ' dBFS)'
    print 'fs:             ' + str(fs) + ' Hz'
    print 'N:              ' + str(N) + ' (test signal total lenght in samples)'
    print 'Duration:       ' + str(round((N/float(fs)), 2)) + ' s (N/fs)'
    print 'Time clearance: ' + str( round(N/(4.0*fs), 2) )
    print 'System_type:    ' + system_type
    print
    return

def plot_spectrum(MAG, fs=fs, semi=False, fini=20, fend=20000,
                  fig=None, label=" ", color="blue"):
    """ plotea un espectro 'mag'
        semi: boolean que indica que 'mag' es un semiespectro
    """
    if semi:
        N = len(MAG)*2
    else:
        N = len(MAG)
    Kbins = str((N/2)/1024)
    Fresol = float(fs)/N
    #frecs = arange(0, N/2.0) * fs / N
    frecs = linspace(0, fs/2, N/2)
    #top  = 20 * log10(max(abs(TF[0:N/2])))  # highest dB in plot
    top = 0
    MAGdB = 20 * log10(abs( MAG[0:N/2] ))
    plt.figure(fig)
    plt.semilogx(frecs, MAGdB, color, label=label)
    plt.grid()
    plt.xlim( minFrecPlot, fs/2 )
    plt.ylim( top+dBclearance-dBspan, top+dBclearance )
    plt.xlim(fini, fend)
    plt.legend()
    plt.xlabel('frequency [Hz]')
    plt.ylabel('dB')
    plt.title('Magnitude Response (' + Kbins + ' Kbins, res = ' + str(round(Fresol,2)) + ' Hz)')
    return

def make_sweep():
    """ returns:    (windowsweep, sweep, Npad)
                    The sequence to be played: faded sweep + end pad zeroes
                    The raw one.
    """
    global Npad, indexf1, indexf2           # necesarias en otros procedimientos
    
    # La secuencia total enviada tendrá longitud N (2**xx) muestras , pero
    # el sweep no las ocupará todas, se deja al final un tramo de 'Npad' zeros
    Npad = N/4                              # zeros at the end of the total sequence
    Ns   = N - Npad                         # most of array is used for sweep
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

    print "--- Calculating logsweep from ", int(f_start), "to", int(f_stop), "Hz"
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
    windosweep = windo * sweep  # Here the LOGSWEEP tapered at each end for output to DAC

    # NOTA no tengo claro el interés de pritar esto:
    print "f_start * Ls: " + str(round(f_start*Ls, 2)) + \
          "   Ls: "  + str(round(Ls,2)) + "    ¿!?"
    print 'Finished sweep generation...'
    print
    # ---- Plot del sweep (domT)
    if auxPlots:
        plt.figure(10)
        vSamples = arange(0,N)              # vector de samples
        vTimes   = vSamples / float(fs)     # samples a tiempos para visualización
        plt.plot(vTimes, sweep,      color='red',  label='raw sweep')
        plt.grid()
        plt.plot(vTimes, windosweep, color='blue', label='windowed sweep')
        plt.ylim(-1.5, 1.5)
        plt.xlabel('time[s]')
        plt.legend()
        plt.title('Sweeps')

    return windosweep, sweep

def get_offset_xcorr(sweep, dut, ref):
    """
    Determines CLEARANCE based on the offset found between recorded and played signals.
    The offset is estimated by using crosscorrelation within them.
    
    If the offset exceeds the ending silence (Npad zeros), then information will be lost
    and CLEARANCE warning appears.
    
    returns: offset, TimeClearanceOK

    """
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
        print "(i) Bad level on REF ch, using DUT ch itself to estimate clearance"

    print "--- Determining record/play delay using crosscorrelation (can take a while ...)"
    TimeClearanceOK = False
    timestamp = time()

    ### (i) Correlation in NUMPY/SCIPY no usa el parámetro lags como en MATLAB
    
    # Correlate de Numpy tarda mucho, usamos el de signal 
    # PEEEERO escupe un FutureWarning al menos en mi versión 
    # que queda feo en la consola :-/
    X = signal_correlate(sweep, myref, mode="same")
    offset = N/2 - argmax(X)

    print "Computed in " + str( round(time() - timestamp, 1) ) + " s"

    if auxPlots:
        t  = arange(0, N) / float(fs) # linea de tiempo
        t -= N/2.0 / fs               # centramos el 0 en el pico ideal de X
        plt.figure(30)
        plt.plot(t, X, color="black", label='xcorr pb/rec')
        plt.grid()
        plt.legend()
        plt.xlabel('time (s)')
        plt.title('recorder lags  player <----|----> recorder leads player')

    print 'Record offset: ' +  str(offset) + ' samples' + \
          ' (' +  str( round( offset/float(fs), 3) ) + ' s)'
    if offset < 0:
        print '(i) Negative offset means player lags recorder!'

    if abs(offset) > Npad:
        print '******INSUFFICIENT TIME CLEARANCE!******'
        print '******INSUFFICIENT TIME CLEARANCE!******'
        print '******INSUFFICIENT TIME CLEARANCE!******'
    else:
        TimeClearanceOK = True

    return offset, TimeClearanceOK

def do_meas(windosweep, sweep):
    """
    returns:    DUT_SWEEP (The Transfer Function of the DUT),
                    If errors, returns zeros(N)
    """
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
        print "(!) Please check system_type for CF"
        return zeros(N)
    
    #-----------------------------------------------------------------------------
    #------------ 2. data gathering: send out sweep, record system output --------
    #-----------------------------------------------------------------------------
    print '--- Starting recording ...'
    print '(i) Some sound cards act strangely. Check carefully!'
    # Antiphased signals on channels avoids codec midtap modulation.
    # Se aplica atenuación según 'sig_frac'
    stereo = array([sig_frac * windosweep, sig_frac * -windosweep]) # [ch0, ch1]
    sd.default.samplerate = fs
    sd.default.channels = 2
    # (i) .transpose pq el player necesita una array con cada canal en una COLUMNA.
    z = sd.playrec(stereo.transpose(), blocking=True) # 'blocking' waits to finish.
    dut = z[:, 0]   # we use LEFT  CHANNEL as DUT
    ref = z[:, 1]   # we use RIGHT CHANNEL as REFERENCE
    #N   = len(dut) # esto creo que es innecesario
    print 'Finished recording.'

    #---------------------------  Cheking LEVELS -----------------------------------
    print "--- Checking levels:"
    maxdBFS_DUT = 20 * log10( max( abs( dut ) ) )
    maxdBFS_REF = 20 * log10( max( abs( ref ) ) )
    # Esto supongo que debe ser una información de energía ¿?
    DUT_RMS_LSBs = round(sqrt( 2**30 * sum(dut**2) / N ), 2)
    REF_RMS_LSBs = round(sqrt( 2**30 * sum(ref**2) / N ), 2)

    if maxdBFS_DUT >= clipWarning:
        print 'DUT channel max level:', round(maxdBFS_DUT, 1), 'dBFS  WARNING (!)', \
              'RMS_LSBs:',  DUT_RMS_LSBs
    else:
        print 'DUT channel max level:', round(maxdBFS_DUT, 1), 'dBFS             ', \
              'RMS_LSBs:',  DUT_RMS_LSBs

    if maxdBFS_REF >= clipWarning:
        print 'REF channel max level:', round(maxdBFS_REF, 1), 'dBFS  WARNING (!)', \
              'RMS_LSBs:',  REF_RMS_LSBs
    else:
        print 'REF channel max level:', round(maxdBFS_REF, 1), 'dBFS             ', \
              'RMS_LSBs:',  REF_RMS_LSBs

    #--- Plots time domain de la grabación del DUT y del REFERENCE LOOP
    if auxPlots:
        plt.figure(20)
        vTimes = arange(0,N) / float(fs)    # vector de samples en segundos
        plt.plot(vTimes, dut,       'blue', label='raw dut')
        plt.plot(vTimes, ref + 2.0, 'grey', label='raw ref (offset+2.0)')
        plt.grid()
        plt.ylim(-1.5, 3.5)
        plt.legend()
        plt.xlabel('Time [s]')
        plt.title('Recorded responses');

    #-----------------------------------------------------------------------------
    #------------- 3. Determine if time clearance: -------------------------------
    # Checks if ound card play/rec delay is lower than the zeropad silence at the signal end.
    # ( Will use crosscorrelation )
    #-----------------------------------------------------------------------------
    offset = 0.0 # ideal record/play delay
    TimeClearanceOK = True # forzamos aunque pudiera ser falso.
    if checkClearence:
        offset, TimeClearanceOK = get_offset_xcorr(sweep=sweep, dut=dut, ref=ref)

    #-----------------------------------------------------------------------------
    #-------------- 4. Calculate TFs using Frequency Domain Ratios * -------------
    #                   UCASE used for freq domain variables.
    #                   All frequency variables are meant to be voltage spectra
    #-----------------------------------------------------------------------------
    lwindo = ones(N)
    lwindo[0:indexf1] = 0.5 * ( 1- cos ( pi * arange(0,indexf1) / indexf1 ) ) # LF pre-taper
    lwindosweep = lwindo * sweep
    # remove play-record delay by shifting computer sweep array:
    ## %sweep=circshift(sweep,-offset);             # Esto aparece comentado en el cód. original,
    ## lwindosweep=circshift(lwindosweep,-offset);  # que usa este código.
    lwindosweep = roll(lwindosweep, -offset)

    # (i) NÓTESE que trabajamos con FFTs completas:
    LWINDOSWEEP = S_dac * fft.fft(lwindosweep) * sig_frac   # sig_frac es la atenuación establecida al sweep
    REF         = S_adc * fft.fft(ref)
    DUT         = S_adc * fft.fft(dut)         * CF         # CF calibration factor

    # (i) La DECONVOLUCIÓN, mediante división en el dominio de la frecuencia
    #     - o sea los 'Frequency Domain Ratios' referidos arriba(*) -
    #     proporciona la TF Transfer Function del dispositivo bajo ensayo DUT
    #     que es el objetivo que nos ocupa ;-)

    ##%TF       = DUT./SWEEP;                                # <- código original comentado
    DUT_SWEEP   = DUT / LWINDOSWEEP  # (orig named as 'TF' )   this has good Nyquist behaviour
    DUT_REF     = DUT / REF          # (orig named as 'TF2')

    #-----------------------------------------------------------------------------
    #-------------------------  PLOTTING FREQ RESPONSES --------------------------
    #-----------------------------------------------------------------------------
    if TFplot:
        plot_spectrum(DUT_SWEEP, fig=100, label='DUT/SWEEP', color='blue')
        plot_spectrum(DUT_REF,   fig=100, label='DUT/REF',   color="grey")

        if plotSmoothSpectrum:
            # Para aligerar el trabajo de suavizado, que tarda mucho,
            # preparamos una versión reducida de DUT_SWEEP

            frecOrig = arange(0, N/2.0)  * fs / N
            magOrig  = DUT_SWEEP[0:N/2] # tomamos solo el semiespectro positivo

            N2 = N/4                    # remuestreo a un cuarto para aligerar
            frecNew  = arange(0, N2/2.0) * fs / N2
            # Definimos la func. de interpolación que nos ayudará a obtener las mags reducidas
            funcI = interpolate.interp1d(frecOrig, magOrig, kind="cubic", bounds_error=False,
                                     fill_value="extrapolate")
            # Obtenemos las magnitudes interpoladas en las 'fnew':
            magNew = funcI(frecNew)

            print "--- Smoothing DUT spectrum (this can take a while ...)"
            t_start = time()
            # (i) 'audiotools.smooth' trabaja con semiespectros positivos y reales (no complejos)
            smoothed = smooth(abs(magNew), frecNew, Noct=24)
            plot_spectrum(smoothed, semi=True, fig=100, color='green', label='DUT/SWEEP smoothed')
            print "Smoothing computed in " + str( round(time() - t_start, 1) ) + " s"

    ### (i)
    ##  A partir de aquí , el código original de Logsweep1quasi.m está destinado a
    ##  encontrar la respuesta quasi anecoica de un altavoz, a base de definir marcadores para
    ##  enventanar la medida DUT.
    ##  A nosotros nos interesa la respuesta estacionaria in room.

    if TimeClearanceOK:
        return DUT_SWEEP
    else:
        return zeros(N)

#-----------------------------------------------------------------------------
#--------------------------------- MAIN PROGRAM ------------------------------
#-----------------------------------------------------------------------------
if __name__ == "__main__":

    # Las gráficas son mostradas por defecto
    TFplot      = True
    auxPlots    = True
    
    # Lee la command line
    opcsOK = True
    for opc in sys.argv[1:]:

        if "-h" in opc.lower():
            print __doc__
            print "    SYSTEM SOUND DEVICES:\n"
            print sd.query_devices()
            print
            sys.exit()

        elif "-noinfo" in opc.lower():
            printInfo = True

        elif "-notf" in opc.lower():
            TFplot = False

        elif "-noaux" in opc.lower():
            auxPlots = False

        elif "-smoo" in opc.lower():
            plotSmoothSpectrum = True

        elif "-noclear" in opc.lower():
            checkClearence = False

        elif opc.lower() == "-sc":
            select_card = True
 
        elif "-dev" in opc.lower():
            try:
                selected_card = opc.split("=")[1]
                if not selected_card:
                    print __doc__
                    sys.exit()
            except:
                print __doc__
                sys.exit()

        elif "-e" in opc:
            N = 2**int(opc[2:])

        else:
            opcsOK = False

    if not opcsOK:
        print __doc__
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
            print "(!) Error using devices to play/rec:"
            for dev in sd.default.device:
                print "    " + sd.query_devices(dev)['name']
            sys.exit()

    if printInfo:
        do_print_info()

    windosweep, sweep = make_sweep()
    
    TF = do_meas(windosweep, sweep)

    if auxPlots or TFplot:
        print "--- Showing the graphs..."
        plt.show()
