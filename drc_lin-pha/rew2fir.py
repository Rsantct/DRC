#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Genera FIRs para DRC a partir de los filtros paramétricos
    de archivos .txt provinientes de Room EQ Wizard.
    
    Experimental: Además de FIR min-phase, también genera
                  el equivalente linear-phase con la misma
                  respuesta en magnitud.
"""
from scipy import signal

# Para que este script pueda estar fuera de ~/audiotools
import os
import sys
HOME = os.path.expanduser("~")
sys.path.append(HOME + "/audiotools")
# modulos de audiotools:
import utils
import pydsd

# PARAMETROS GLOBALES:
fs = 44100  # Frecuencia de muestreo
m  = 2**15  # Longitud del impulso FIR
            # (i) Para filtros de alto Q > 5  y baja frecuencia <50Hz
            #     usar m >= 16K para un FIR largo.

for channel in "L", "R":

    # 0. Partimos de una delta (espectro plano)
    imp = pydsd.delta(m)

    # 1. Aplicamos una curva Room Gain +6dB
    #gain = 6.0
    #imp = utils.RoomGain2impulse(imp, fs, gain)

    # 2. Leemos los filtros paramétricos desde un archivo de texto de REW:
    rewfname = "rew_" + channel + ".txt"
    PEQs = utils.read_REW_EQ_txt(rewfname)

    # 3. Encadenamos los filtros 'peakingEQ' 
    for peqId, params in PEQs.items():

        b, a = pydsd.biquad(fs     = fs, 
                            f0     = params['fc'], 
                            Q      = params['Q'], 
                            dBgain = params['gain'],
                            type   = "peakingEQ") 

        imp = signal.lfilter(b, a, imp)

    # 4. Guardamos el resultado minimum phase
    utils.savePCM32(imp, "biquads_" + channel + ".pcm")

    # 5. Convertimos a LP linear phase :-| ejem...
    imp = utils.MP2LP(imp, windowed=True, kaiserBeta=1)

    # 6. Guardamos el resultado LP
    utils.savePCM32(imp, "biquads_lp_" + channel + ".pcm")

print "(i) Observar los resultados haciendo zoom con"
print "    'IRs_viewer.py biquads_R.pcm biquads_lp_R.pcm 44100'"
print
print "    Es interesante probar distintas fs, betas de kaiser..."
print "    Si aumentamos beta disminuyen los microartifactos del GD del filtro, ¿audibles?,"
print "    pero a costa de menos resolución en la curva de filtrado en graves."

