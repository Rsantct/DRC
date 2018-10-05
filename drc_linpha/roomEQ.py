#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    roomEQ.py v0.1a

    Ecualiza una respuesta en frecuencia in room.

    Uso:    python roomEQ.py respuesta.frd  -fs=xxxxx  [-ref=xx] [-v]

            -fs     48000 por defecto
            -ref    Nivel de referencia en dB (autodetectado por defecto)
            -v      Visualiza los impulsos FIR generados

    Se necesita  github.com/AudioHumLab/audiotools

"""
#
# v0.1a
#   - Nombrado de archivos de salida para FIRtro
#   - Muestra la correspondencia del nivel de referencia estimado en el gráfico

# AJUSTES POR DEFECTO:
m               = 2**15       # Longitud del FIR por defecto 2^15=32K
fs              = 48000
esParaFIRtro    = True
autoRefLevel    = True
verFIRs         = False

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

# Módulo de AudioHumLab/audiotools
from smoothSpectrum import smoothSpectrum as smooth

# Módulos estandar
import numpy as np
from scipy import signal
from matplotlib import pyplot as plt

# 1. LECTURA DE LA CURVA A PROCESAR y otros argumentos
if len(sys.argv) == 1:
    print __doc__
    sys.exit()

for opc in sys.argv[1:]:

    if opc[0] <> '-' and opc[-4:] in ('.frd','.txt'):
        FRDname = opc
        # Lee el contenido del archivo .frd
        FR = utils.readFRD(FRDname)
        frec = FR[:, 0]     # array de frecuencias
        mag  = FR[:, 1]     # array de magnitudes

    elif opc[:4] == '-fs=':
        if opc[4:] in ('44100', '48000', '96000'):
            fs = int(opc[4:])
        else:
            print "fs debe ser 44100 | 48000 | 96000"
            sys.exit()

    elif '-v' in opc:
        verFIRs = True

    elif opc[:5] == '-ref=':
        try:
            ref_level = opc[5:]
            ref_level = round( float(ref_level), 1)
            autoRefLevel = False
        except:
            print __doc__
            sys.exit()

    else:
        print __doc__
        sys.exit()

# Confirmamos si la fs está en el archivo .frd
if not os.system("grep \ " + str(fs) + " " + FRDname + "> /dev/null 2>&1"):
    tmp = " coincide con la indicada en " + FRDname
else:
    tmp = " debe ser la de la DFT con que se ha calculado " + FRDname
print "fs: " + str(fs) + tmp
print "          (usada solo para visualizar los impulsos generados)"

# 1a. PREMISA: el primer bin de 'frec' debe ser 0 Hz
if frec[0] <> 0:
    # nos inventamos el bin zero
    frec = np.insert(frec, 0, 0)
    mag  = np.insert(mag,  0, mag[0])

# 2. CALCULO DE LA EQ

# 2.1 'ref_level': NIVEL DE REFERENCIA
# Curva muy suavizada 1/1oct que usaremos para tomar el nivel de referencia
rmag = smooth(mag, frec, Noct=1)
if autoRefLevel:
    ###########################################################
    # Rango de frecuencias para decidir el nivel de referencia:
    f1, f2 = 400, 4000
    ###########################################################
    f1_idx = (np.abs(frec - f1)).argmin()
    f2_idx = (np.abs(frec - f2)).argmin()
    # magnitudes del rango de referencia:
    r2mag = rmag[ f1_idx : f2_idx ]
    # Vector de pesos para calcular el promedio
    weightslograte = .5
    weights = np.logspace( np.log(1), np.log(weightslograte), len(r2mag) )
    # Calculamos el nivel de referencia
    ref_level = round( np.average( r2mag, weights=weights ), 2)
    print "Nivel de referencia estimado: " +  str(ref_level) + " dB --> 0 dB"
else:
    print "Nivel de referencia: " +  str(ref_level) + " dB --> 0 dB"

# 2.2 'smag': CURVA SUAVIZADA QUE USAREMOS PARA ECUALIZAR
Noct = 48           # Suavizado fino inicial 1/48 oct
f0  = 120           # Frec de transición de suavizado fino hacia 1/1 oct
Tspeed = "medium"   # Velocidad de transición del suavizado
smag = smooth(mag, frec, Noct, f0=f0, Tspeed=Tspeed)

# 2.3 Recolocamos las curvas en el nivel de referencia:
mag  -= ref_level
rmag -= ref_level
smag -= ref_level

# 3. 'eq': CALCULO DE LA EQ
# 3.1 Invertimos la respuesta:
eq  = -smag
# 3.2 Recortamos ganacias positivas:
np.clip(eq, a_min=None, a_max=0.0, out=eq)
# 3.3 Y limamos asperezas:
eq = smooth(eq, frec, Noct=12)

# 4. Computamos el impulso de la EQ y lo guardamos un PCM

# 4.1 Si el semiespectro 'eq' que tenemos se queda corto lo
# completamos con zeros porque son dBs de un curva de EQ
# que no tiene ganancia en los extremos.
extra = m/2 - len(eq)
if extra > 0:
    eq_v2 = np.concatenate( (eq, np.zeros(extra)) )
else:
    eq_v2 = np.copy(eq)

# 4.2 Si el semiespectro es de longitud EVEN, lo hacemos ODD
if len(eq_v2) % 2 == 0:
    eq_v2 = np.insert(eq_v2, -1, eq_v2[-1])

# 4.3 dB --> gain
eq_v2 = 10.0**(eq_v2/20.0)

# 4.4 Computamos el impulso calculando la IFFT de la curva del EQ.
#     OjO nuestra curva semiespectro de EQ es una abstracción reducida a magnitudes,
#     pero la IFFT necesita un espectro real (con phase minima) y completo (simétrico)
sp = pydsd.minphsp( pydsd.wholespmp(eq_v2) ) # Si lo printamos veremos que tiene phase
imp = np.real( np.fft.ifft( sp ) )
imp = pydsd.semiblackmanharris(m) * imp[:m]

# Ahora 'imp' tiene una respuesta 'natural', o sea de phase mínima.

# 4.5 Versión linear-phase (experimental) ...
impLP = utils.MP2LP(imp, windowed=True, kaiserBeta=1)

# 4.6 Guardamos los impulsos en archivos .pcm

# Nombramos los pcm:
if esParaFIRtro:
    ch = 'C' # genérico por si no viene nombrado el frd
    if FRDname[0].upper() in ('L','R'):
        ch = FRDname[0].upper()
        resto = FRDname[1:-4].strip().strip('_').strip('-')
    mpEQpcmname = 'drc-X-'+ch+'_mp_'+resto+'.pcm'
    lpEQpcmname = 'drc-X-'+ch+'_lp_'+resto+'.pcm'
else:
    mpEQpcmname = "mp_" + FRDname.replace('.frd', '_EQ.pcm').replace('.txt', '_EQ.pcm')
    lpEQpcmname = "lp_" + FRDname.replace('.frd', '_EQ.pcm').replace('.txt', '_EQ.pcm')

# Guardamos:
utils.savePCM32(imp,   mpEQpcmname)
utils.savePCM32(impLP, lpEQpcmname)

print "Guardando el FIR de ecualización en '" + mpEQpcmname + "' '" + lpEQpcmname + "'"

# 5. PLOTEOS
# Curva inicial sin suavizar
plt.semilogx(frec, mag,
             label="raw", color="silver", linestyle=":")

# Curva suavizada
plt.semilogx(frec, smag,
             label="smoothed", color="blue")

# Cacho de curva usada para calcular el nivel de referencia
if autoRefLevel:
    plt.semilogx(frec[ f1_idx : f2_idx], rmag[ f1_idx : f2_idx ],
                 label="ref level range", color="black", linestyle="--", linewidth=2)

# Curva de EQ
plt.semilogx(frec, eq,
             label="EQ", color="red")
tmp = FRDname + "\n(ref. level @ " + str(ref_level) + " dB --> 0 dB)"
plt.title(tmp)
plt.xlim(20, 20000)
plt.ylim(-30, 10)
plt.grid()
plt.legend()
plt.show()

# 6. Guardamos las gráficas en un PDF:
#pdfName = FRDname.replace('.frd', '_eq.pdf').replace('.txt', '_eq.pdf')
#print "\nGuardando gráfica en el archivo " + pdfName
# evitamos los warnings del pdf
# C:\Python27\lib\site-packages\matplotlib\figure.py:1742: UserWarning:
# This figure includes Axes that are not compatible with tight_layout, so
# its results might be incorrect.
import warnings
#warnings.filterwarnings("ignore")
#fig.savefig(pdfName, bbox_inches='tight')

# 7. Veamos los FIRs de EQ:
if verFIRs:
    print "Veamos los impulsos con audiotools/IRs_viewer.py ..."
    os.system("IRs_viewer.py '" + lpEQpcmname + "' '" + mpEQpcmname + "' 20-20000 -eq -1 " + str(int(fs)))

# FIN
