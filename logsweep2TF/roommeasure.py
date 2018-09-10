#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Script para la medida de la respuesta estacionaria de una sala.

    Se obtiene:

    'room_avg.frd'           Promedio de medidas en varios puntos de escucha
    'room_avg_smoothed.frd'  Promedio suavizado 1/24 oct hasta la Freq Schroeder
                             y progresivamente hacia 1/1 oct en Freq Nyq.

    Uso: python roommeasure.py  [opciones ... ...]

         -h                 ayuda

         -Mxx               Número de medidas a realizar.
         -Exx               Potencia de 2 que determina la longitud=2^xx
                            en muestras de la señal de prueba. Por defecto 2^17.

         -Sxx               Freq Shroeder para el suavizado, por defecto 200 Hz.

         -dev=cap,pbk,fs    Usa los sound devices y la fs indicada.
                            (Ver dispositivos con logsweep2TF.py -h)

    IMPORTANTE:
    Se recomienda una prueba previa con logsweep2TF.py para verificar que:
    - La tarjeta de sonido no pierde muestras y los niveles son correctos.
    - La medida es viable (Time clearance) con los parámetros usados.
"""

import sys
from numpy import *
from scipy import interpolate
try:
    import logsweep2TF as LS
except:
    print "(!) Se necesita logsweep2TF.py"
    sys.exit()

# DEFAULTS

LS.N                    = 2**17     # Longitud en muestras de la señal de prueba.
numMeas                 = 2         # Núm de medidas a realizar

Scho                    = 200       # Frec de Schroeder (Hz)
Noct                    = 24        # Suavizado hasta Schroeder de la medida final promediada

#LS.sd.default.xxxx                 # Tiene valores por defecto en logsweep2TF

LS.printInfo            = True      # Para que logsweep2TF informe de su  progreso

LS.checkClearence       = False     # Se da por hecho que se ha comprobado previamente.

LS.TFplot               = False     # Omite las gráficas de logsweep2TF
LS.auxPlots             = False
LS.plotSmoothSpectrum   = False

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
    selected_card = LS.selected_card

    if selected_card:
        i = selected_card.split(",")[0].strip()
        o = selected_card.split(",")[1].strip()
        try:    fs = int(selected_card.split(",")[2].strip())
        except: pass
        if i.isdigit(): i = int(i)
        if o.isdigit(): o = int(o)
        if not LS.test_soundcard(i=i, o=o):    #  Si falla la tarjeta indicada en command line.
            sys.exit()

    # ejem..
    N             = LS.N
    fs            = LS.fs

    # 1. Preparamos el sweep
    windosweep, sweep = LS.make_sweep()

    # 2.Hacemos la primera medida, tomamos el semiespectro
    semiTFs = abs( LS.do_meas(windosweep, sweep)[:N/2] )
    #   y añadimos el resto:
    for m in range(1,numMeas):
        print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        print "PULSA INTRO PARA REALIZAR LA SIGUIENTE MEDIDA"
        print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        raw_input()
        semiTFs = vstack( ( semiTFs, abs( LS.do_meas(windosweep, sweep)[:N/2] ) ) )

    # 3. Calculamos el promedio de todas las medidas raw
    print "Calculando el promedio"
    if numMeas > 1:
        # Calculamos el PROMEDIO de todas las medidas realizadas
        semiTFsAvg = average(semiTFs, axis=0)
    else:
        semiTFsAvg = semiTFs

    # 4. SUAVIZADO VARIABLE desde 200Hz aumentamos el suavizado hasta 1/1 oct.
    # 4.1 Para aligerar el trabajo de suavizado, que tarda mucho,
    #     preparamos una versión reducida
    Nnew = 2**14 # 16K bins
    frecOrig = linspace(0, fs/2, N/2)
    magOrig  = semiTFsAvg
    frecNew  = linspace(0, fs/2, Nnew/2)
    #     Definimos la func. de interpolación que nos ayudará a obtener las mags reducidas
    funcI = interpolate.interp1d(frecOrig, magOrig, kind="linear", bounds_error=False,
                         fill_value="extrapolate")
    #     Y obtenemos las magnitudes interpoladas en las 'frecNew':
    magNew = funcI(frecNew)

    # 4.2 Procedemos con el suavizado sobre la versión reducida
    print "Suavizando 1/" + str(Noct) + " oct hasta " + str(Scho) + " Hz y variable hasta Nyq"
    smoothed = LS.smooth(magNew, frecNew, Noct=Noct, f0=Scho)

    # Guardamos las respuestas en frecuencia raw y smoothed en archivos .FRD
    header =  "DFT Frequency Response\n"
    header += "Numpoints = " + str(len(frecNew)) + "\n"
    header += "SamplingRate = " + str(fs) + " Hz\n"
    header += "Frequency(Hz)   Magnitude(dB)"

    # Raw
    fname = "room_avg.frd"
    print "Guardando " + fname
    savetxt( fname, column_stack((frecNew, 20*log10(magNew))), 
             delimiter="\t", fmt='%1.4e', header=header)
    # Smoothed
    fname = "room_avg_smoothed.frd"
    print "Guardando " + fname
    savetxt( fname, column_stack((frecNew, 20*log10(smoothed))), 
             delimiter="\t", fmt='%1.4e', header=header)

    # Muestra la respuesta en frecuencia calculada.
    LS.plot_spectrum(magNew,   semi=True, fig=10, color='blue', label='avg')
    LS.plot_spectrum(smoothed, semi=True, fig=10, color='red',  label='avg smoothed')
    LS.plt.show()


