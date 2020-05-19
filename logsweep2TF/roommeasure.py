#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    Script para obtener la respuesta estacionaria de una sala,
    en varios puntos de escucha (micrófono).

    Se obtiene:

    'room_X.frd'             Medidas en cada punto de escucha X.
    'room_avg.frd'           Promedio de medidas en los puntos de escucha
    'room_avg_smoothed.frd'  Promedio suavizado 1/24 oct hasta la Freq Schroeder
                             y progresivamente hacia 1/1 oct en Freq Nyq.

    Uso: python roommeasure.py  [opciones ... ...]

         -h                 ayuda

         -mX                Número de medidas a realizar.
         -eXX               Potencia de 2 que determina la longitud = 2^XX
                            en muestras de la señal de prueba. Por defecto 2^17.
         -cX                Canal: L | R | LR  se usará como prefijo del archivo.frd.
                            LR permite intercalar medidas de cada canal en cada posición de micro.
                            Si se omite se usará el prefijo 'C'.

         -sXX               Freq Shroeder para el suavizado, por defecto 200 Hz.

         -dev=cap,pbk,fs    Usa los números de dispositivo de sonido y la fs indicados.
                            (Ver dispositivos con logsweep2TF.py -h)

         -nobeep            No pita antes de estar listo para medir.

    IMPORTANTE:
    Se recomienda una prueba previa con logsweep2TF.py para verificar que:
    - La tarjeta de sonido no pierde muestras y los niveles son correctos.
    - La medida es viable (Time clearance) con los parámetros usados.

    Se pueden revisar las curvas con FRD_viewer.py del paquete audiotools, p.ej:

        FRD_tool.py $(ls room_?.frd)
        FRD_tool.py $(ls room_?.frd) -24oct -f0=200  # Para verlas suavizadas

"""
# v1.0a
#   Se separa la función medir(secuencia)
# v1.1
#   Opción para intercalar medidas para cada canal en cada punto de micrófono

import sys
from numpy import *
from scipy import interpolate
from scipy.io import wavfile # para leer beepbeep.wav

try:
    import logsweep2TF as LS
except:
    print "(!) Se necesita logsweep2TF.py"
    sys.exit()

#  ~/audiotools modules
import os
import sys
HOME = os.path.expanduser("~")
sys.path.append(HOME + "/audiotools")
try:
    import tools
    from smoothSpectrum import smoothSpectrum as smooth
except:
    raise ValueError("rew2fir.py necesita https://githum.com/AudioHumLab/audiotools")
    sys.exit()
# end of /audiotools modules

# DEFAULTS

LS.N                    = 2**17     # Longitud en muestras de la señal de prueba.
numMeas                 = 2         # Núm de medidas a realizar
avisoBeep               = True      # pitido de aviso antes de medir

binsFRD                 = 2**14     # bins finales de los archivos .frd obtenidos
channels                = 'C'       # Canales a intercalar en cada punto de medida, se usará
                                    # como prefijo del los .frd, p.ej: "L" o "R"

Scho                    = 200       # Frec de Schroeder (Hz)
Noct                    = 24        # Suavizado 1/N oct hasta Schroeder de la medida final promediada,
                                    # pasada la frec Scho se aumentará el suavizado progresivamente hasta 1/1 oct.

#LS.sd.default.xxxx                 # Tiene valores por defecto en logsweep2TF
selected_card           = LS.selected_card

LS.printInfo            = True      # Para que logsweep2TF informe de su  progreso

LS.checkClearence       = False     # Se da por hecho que se ha comprobado previamente.

LS.TFplot               = False     # Omite las gráficas por defecto del módulo logsweep2TF alias LS
LS.auxPlots             = False
LS.plotSmoothSpectrum   = False

def interpSS(freq, mag, Nbins):
    """ Interpola un Semi Spectro a una nueva longitud Nbins
    """
    freqNew  = linspace(0, fs/2, Nbins)
    # Definimos la func. de interpolación para obtener las nuevas magnitudes
    funcI = interpolate.interp1d(freq, mag, kind="linear", bounds_error=False,
                         fill_value="extrapolate")
    # Y obtenemos las magnitudes interpoladas en las 'frecNew':
    return freqNew, funcI(freqNew)

def medir(ch='C', secuencia=0):
    # Hacemos la medida, tomamos el SemiSpectrum positivo
    meas = abs( LS.do_meas(windosweep, sweep)[:N/2] )
    # Guardamos la curva en un archivo .frd secuenciado
    f, m = interpSS(freq, meas, binsFRD)
    tools.saveFRD( ch + '_room_'+str(secuencia)+'.frd', f, 20*log10(m), fs=fs,
                   comments='roommeasure.py ch:' + ch + ' point:' + str(secuencia) )
    # La ploteamos suavizada para mejor visualización (esto tarda en máquinas lentas)
    m_smoo = smooth(f, m, Noct, f0=Scho)
    figIdx = 10
    canales = ('L', 'R', 'C')
    if ch in canales:
        figIdx += canales.index(ch)
    LS.plot_spectrum( m_smoo, semi=True, fig = figIdx,
                      label = ch + '_' + str(secuencia), color='C' + str(secuencia) )
    return meas

def aviso_medida(ch, secuencia):
    aviso =  "\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
    aviso += "PULSA INTRO PARA MEDIR EN CANAL  < " + ch + " >  (" + str(secuencia+1) + "/" + str(numMeas) + ")\n"
    aviso += "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
    print aviso
    if avisoBeep:
        Nbeep = tile(beep, 1+secuencia)
        LS.sd.play(Nbeep)
    raw_input(aviso) # usamos print pq raw_input no presenta el texto :-/

if __name__ == "__main__":

    # Cargamos un pitido por si deseamos avisar antes de cada medida:
    fsbeep, beep = wavfile.read(HOME+"/DRC/logsweep2TF/beep.wav")

    # Leemos los argumentos command line:
    opcsOK = True
    for opc in sys.argv[1:]:

        if "-h" in opc.lower():
            print __doc__
            sys.exit()

        elif "-nobeep" in opc.lower():
            avisoBeep = False

        elif "-dev" in opc.lower():
            try:
                selected_card = opc.split("=")[1]
                if not selected_card:
                    print __doc__
                    sys.exit()
            except:
                print __doc__
                sys.exit()

        elif "-m" in opc:
            numMeas = int(opc[2:])

        elif "-c" in opc:
            channels = [x for x in opc[2:]]

        elif "-s" in opc:
            Scho = int(opc[2:])

        elif "-e" in opc:
            LS.N = 2**int(opc[2:])

        else:
            opcsOK = False

    if not opcsOK:
        print __doc__
        sys.exit()

    LS.sd.default.channels     = 2
    LS.sd.default.samplerate   = float(LS.fs)

    if selected_card:
        i = selected_card.split(",")[0].strip()
        o = selected_card.split(",")[1].strip()
        try:    fs = int(selected_card.split(",")[2].strip())
        except: pass
        if i.isdigit(): i = int(i)
        if o.isdigit(): o = int(o)
        if not LS.test_soundcard(i=i, o=o):    #  Si falla la tarjeta indicada en command line.
            sys.exit()

    # Leemos los valores N y fs que hemos cargado en el módulo LS al leer las opciones -E.. -dev...
    N             = LS.N
    fs            = LS.fs

    # Vector de frecuencias positivas para la N elegida.
    freq = linspace(0, fs/2, N/2)

    # 1. Preparamos el sweep
    windosweep, sweep = LS.make_sweep()

    # 2. Medimos, acumulando en una pila de promediado 'SSs'
    SSs = {}
    SSsAvg = {}
    # Esperamos que se pulse INTRO
    for ch in channels:
        aviso_medida(ch=ch, secuencia=0)
        SSs[ch] = medir(ch=ch, secuencia=0)
    #    Añadimos el resto de medidas si las hubiera:
    for i in range(1, numMeas):
        for ch in channels:
            # Esperamos que se pulse INTRO
            aviso_medida(ch=ch, secuencia=i)
            meas = medir(ch=ch, secuencia=i)
            # Seguimos acumulando en la pila 'SSs'
            SSs[ch] = vstack( ( SSs[ch], meas ) )

    # 3. Calculamos el promedio de todas las medidas raw
    for ch in channels:
        print "Calculando el promedio canal " + ch
        if numMeas > 1:
            # Calculamos el PROMEDIO de todas las medidas realizadas
            SSsAvg[ch] = average(SSs[ch], axis=0)
        else:
            SSsAvg[ch] = SSs[ch]

    # 4. Guarda el promedio raw en un archivo .frd
    i = 0
    for ch in channels:
        f, m = interpSS(freq, SSsAvg[ch], binsFRD)
        tools.saveFRD( ch + '_room_avg.frd', f, 20*log10(m) , fs=fs,
                       comments='roommeasure.py ch:' + ch + ' raw avg' )

        # 5. También guarda una versión suavidaza del promedio en un .frd
        print "Suavizando el promedio 1/" + str(Noct) + " oct hasta " + str(Scho) + \
              " Hz y variando hasta 1/1 oct en Nyq"
        m_smoothed = smooth(f, m, Noct, f0=Scho)
        tools.saveFRD( ch + '_room_avg_smoothed.frd', f, 20*log10(m_smoothed), fs=fs,
                       comments='roommeasure.py ch:' + ch + ' smoothed avg' )

        # 6. Muestra las curvas de cada punto de escucha en una figura,
        #    y las curva promedio y promedio_suavizado en otra figura.
        LS.plot_spectrum(m,          semi=True, fig=20+i, color='blue', label=ch+' avg')
        LS.plot_spectrum(m_smoothed, semi=True, fig=20+i, color='red',  label=ch+' avg smoothed')
        i += 1

    # FIN
    LS.plt.show()
