#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Script para obtenerla respuesta estacionaria de una sala,
    en varios puntos de escucha (micrófono).

    Se obtiene:

    'room_X.frd'             Medidas en cada punto de escucha X.
    'room_avg.frd'           Promedio de medidas en los puntos de escucha
    'room_avg_smoothed.frd'  Promedio suavizado 1/24 oct hasta la Freq Schroeder
                             y progresivamente hacia 1/1 oct en Freq Nyq.

    Uso: python roommeasure.py  [opciones ... ...]

         -h                 ayuda

         -Mxx               Número de medidas a realizar.
         -Exx               Potencia de 2 que determina la longitud=2^xx
                            en muestras de la señal de prueba. Por defecto 2^17.
         -Pxx               String para prefijos 'xx-archivo.frd'

         -Sxx               Freq Shroeder para el suavizado, por defecto 200 Hz.

         -dev=cap,pbk,fs    Usa los sound devices y la fs indicada.
                            (Ver dispositivos con logsweep2TF.py -h)

    IMPORTANTE:
    Se recomienda una prueba previa con logsweep2TF.py para verificar que:
    - La tarjeta de sonido no pierde muestras y los niveles son correctos.
    - La medida es viable (Time clearance) con los parámetros usados.

    Se pueden revisar las curvas con FRD_viewer.py del paquete audiotools, p.ej:

        FRD_tool.py $(ls room_?.frd)
        FRD_tool.py $(ls room_?.frd) -24oct -f0=200  # Para verlas suavizadas

"""
# v1.0a
# Se separa la función medir(secuencia)

import sys
from numpy import *
from scipy import interpolate

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
    import utils
    from smoothSpectrum import smoothSpectrum as smooth
except:
    raise ValueError("rew2fir.py necesita https://githum.com/AudioHumLab/audiotools")
    sys.exit()
# end of /audiotools modules

# DEFAULTS

LS.N                    = 2**17     # Longitud en muestras de la señal de prueba.
numMeas                 = 2         # Núm de medidas a realizar

binsFRD                 = 2**14     # bins finales de los archivos .frd obtenidos
prefix                  = ''        # prefijo del los .frd, p.ej: "L" o "R"

Scho                    = 200       # Frec de Schroeder (Hz)
Noct                    = 24        # Suavizado hasta Schroeder de la medida final promediada

#LS.sd.default.xxxx                 # Tiene valores por defecto en logsweep2TF
selected_card           = LS.selected_card

LS.printInfo            = True      # Para que logsweep2TF informe de su  progreso

LS.checkClearence       = False     # Se da por hecho que se ha comprobado previamente.

LS.TFplot               = False     # Omite las gráficas de logsweep2TF
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

def medir(secuencia=0):
    # Hacemos la medida, tomamos el SemiSpectrum positivo
    meas = abs( LS.do_meas(windosweep, sweep)[:N/2] )
    # Guardamos la curva en un archivo .frd secuenciado
    f, m = interpSS(freq, meas, binsFRD)
    utils.saveFRD( prefix + 'room_'+str(secuencia)+'.frd', f, 20*log10(m), fs=fs )
    # La ploteamos suavizada para mejor visualización (esto tarda en máquinas lentas)
    m_smoo = smooth(m, f, Noct, f0=Scho)
    LS.plot_spectrum(m_smoo, semi=True, fig=10, label=str(secuencia), color='C'+str(secuencia))
    return meas

aviso_siguiente_medida = """
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
PULSA INTRO PARA REALIZAR LA SIGUIENTE MEDIDA
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""

if __name__ == "__main__":

    opcsOK = True
    for opc in sys.argv[1:]:

        if "-h" in opc.lower():
            print __doc__
            sys.exit()

        elif "-dev" in opc.lower():
            try:
                selected_card = opc.split("=")[1]
                if not selected_card:
                    print __doc__
                    sys.exit()
            except:
                print __doc__
                sys.exit()

        elif "-M" in opc:
            numMeas = int(opc[2:])

        elif "-P" in opc:
            prefix = opc[2:] + "-"

        elif "-S" in opc:
            Scho = int(opc[2:])

        elif "-E" in opc:
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
    SSs = medir(secuencia=0)
    #    Añadimos el resto de medidas si las hubiera:
    for i in range(1, numMeas):
        # Esperamos que se pulse INTRO
        print aviso_siguiente_medida
        raw_input(aviso_siguiente_medida) # usamos print pq raw_input no presenta el texto :-/
        meas = medir(secuencia=i)
        # Seguimos acumulando en la pila 'SSs'
        SSs = vstack( ( SSs, meas ) )

    # 3. Calculamos el promedio de todas las medidas raw
    print "Calculando el promedio"
    if numMeas > 1:
        # Calculamos el PROMEDIO de todas las medidas realizadas
        SSsAvg = average(SSs, axis=0)
    else:
        SSsAvg = SSs

    # Guarda el promedio raw en un archivo .frd
    f, m = interpSS(freq, SSsAvg, binsFRD)
    utils.saveFRD( prefix + 'room_avg.frd', f, 20*log10(m) , fs=fs)

    # También guarda una versión suavidaza del promedio en un .frd
    print "Suavizando el promedio 1/" + str(Noct) + " oct hasta " + str(Scho) + \
          " Hz y variando hasta 1/1 oct en Nyq"
    m_smoothed = smooth(m, f, Noct, f0=Scho)
    utils.saveFRD( prefix + 'room_avg_smoothed.frd', f, 20*log10(m_smoothed), fs=fs)

    # Muestra las curvas de cada punto de escucha en una figura,
    # y las curva promedio y promedio_suavizado en otra figura.
    LS.plot_spectrum(m,          semi=True, fig=20, color='blue', label='avg')
    LS.plot_spectrum(m_smoothed, semi=True, fig=20, color='red',  label='avg smoothed')
    LS.plt.show()

    # FIN

