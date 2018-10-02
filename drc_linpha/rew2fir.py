#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    v0.2
    Genera FIRs para DRC a partir de los filtros paramétricos
    de archivos .txt provinientes de Room EQ Wizard.

    Uso:
            rew2fir.py archivoREW.txt [fs] [xxK]
            fs:  por defecto 44100 (Hz)
            xxK: Ktaps del FIR, por defecto 32K taps

    Experimental: Además de FIR min-phase, también genera
                  el equivalente linear-phase con la misma
                  respuesta en magnitud.

    Es interesante probar distintos valores fs, taps, betas de kaiser...
    Si aumentamos beta disminuyen los microartefactos del GD del filtro, ¿audibles?,
    pero a costa de menos resolución en la curva de filtrado en graves.

    NOTA: se necesita tener instalado el paquete 'AudioHumLab/audiotools'
"""
from scipy import signal

# Para que este script pueda estar fuera de ~/audiotools
import os
import sys
HOME = os.path.expanduser("~")
sys.path.append(HOME + "/audiotools")
# modulos de audiotools:
try:
    import utils
    import pydsd
except:
    raise ValueError("rew2fir.py necesita https://githum.com/AudioHumLab/audiotools")
    sys.exit()

# PARAMETROS GLOBALES POR DEFECTO:
fs = 44100  # Frecuencia de muestreo
m  = 2**15  # Longitud del impulso FIR
            # (i) Para filtros de alto Q > 5  y baja frecuencia <50Hz
            #     usar m >= 16K para un FIR largo.

# 0. LECTURA DEL ARCHIVO .txt de filtros paramétricos de REW
if len(sys.argv) == 1:
    print __doc__
    sys.exit()
rewfname = sys.argv[1]
for opc in sys.argv[1:]:
    if opc.isdigit():
        fs = int(opc)
    if "K" in opc.upper():
        k = int( opc.upper().replace("K", "") )
        m = 1024 * k

# 1. Partimos de una delta (espectro plano)
imp = pydsd.delta(m)

# 2. Aplicamos una curva Room Gain +6dB
#gain = 6.0
#imp = utils.RoomGain2impulse(imp, fs, gain)

# 3. Leemos los filtros paramétricos desde un archivo de texto de REW:
PEQs = utils.read_REW_EQ_txt(rewfname)

# 4. Encadenamos los filtros 'peakingEQ'
for peqId, params in PEQs.items():

    # Printado de paramétricos:
    print  ("  fc: "    + str(   int(params['fc']      ) ) ).ljust(12) + "   " + \
             ("Q: "     + str( round(params['Q'], 2    ) ) ).ljust(12) + "   " + \
             ("dB: "    + str( round(params['gain'], 1 ) ) ).ljust(12) + "   " + \
             "(BWoct: " + str( round(params['BW'], 3 ) )               + ")"

    # Calculamos los coeff IIR correspondientes:
    b, a = pydsd.biquad(fs     = fs,
                        f0     = params['fc'],
                        Q      = params['Q'],
                        dBgain = params['gain'],
                        type   = "peakingEQ"
                       )

    # Aplicamos los coeff a nuestro impulso de partida
    imp = signal.lfilter(b, a, imp)

# 5. Guardamos el resultado (que es minimum phase)
dirname = "/".join(rewfname.split("/")[:-1])
fname   = rewfname.split("/")[-1]
pcmname_mp = "mp-" + fname.replace('.txt', '.pcm')
if dirname:
    pcmname_mp = dirname + "/" + pcmname_mp
utils.savePCM32(imp, pcmname_mp)

# 6. Convertimos a LP linear phase (experimental) ...
imp = utils.MP2LP(imp, windowed=True, kaiserBeta=1)

# 7. Guardamos el resultado LP
pcmname_lp = pcmname_mp.replace('mp-', 'lp-')
utils.savePCM32(imp, pcmname_lp)

print "Guardados FIRs: ", pcmname_mp, pcmname_lp

# 8. Veamos los FIRs de EQ:
os.system("IRs_viewer.py " + pcmname_mp + " " + pcmname_lp + " 20-20000 -eq -1 " + str(int(fs)))
