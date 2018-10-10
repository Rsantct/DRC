#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    roomEQ.py

    Calcula un FIR para ecualizar la respuesta de una sala.

    Uso:
        python roomEQ.py respuesta.frd  -fs=xxxxx  [ -ref=XX  -scho= XX e=XX -v ]

        -fs=    48000 por defecto
        -e=     Longitud del FIR en taps 2^XX (por defecto 2^14 = 16 Ktaps)
        -ref=   Nivel de referencia en XX dB (autodetectado por defecto)
        -scho=  Frecuencia de Schroeder (por defecto 200 Hz)
        -v      Visualiza los impulsos FIR generados

    Se necesita  github.com/AudioHumLab/audiotools

"""
#
# v0.1a
#   - Nombrado de archivos de salida para FIRtro
#   - Muestra la correspondencia del nivel de referencia estimado en el gráfico
# v0.1b
#   - Longitud del FIR y nivel de referencia en command line.
#   - Revisión del cómputo del FIR

##########################################################################
# AJUSTES POR DEFECTO:

# Salida:
m       = 2**14     # Longitud del FIR por defecto 2^14 = 16 Ktaps
fs      = 48000     # fs del FIR de salida
verFIRs = False

# Nivel de referencia:                   
autoRef = True
f1, f2  = 400, 4000 # Rango de frecs. para decidir el nivel de referencia

# TARGET sobre la curva .frd original
Noct    = 48        # Suavizado fino inicial 1/48 oct
fScho   = 200       # Frec de Schroeder
octScho = 1         # Octavas respecto a la freq. Schoeder para iniciar 
                    # la transición de suavizado fino hacia 1/1 oct
Tspeed  = "medium"  # Velocidad de transición del suavizado audiotools/smoothSpectrum.py

##########################################################################
# IMPORTA MODULOS
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

##########################################################################
# 0 LEE ARGUMENTOS
##########################################################################

if len(sys.argv) == 1:
    print __doc__
    sys.exit()

for opc in sys.argv[1:]:

    if opc[0] <> '-' and opc[-4:] in ('.frd','.txt'):
        FRDname = opc
        # Lee el contenido del archivo .frd
        FR, fs_FRD = utils.readFRD(FRDname)
        freq = FR[:, 0]     # >>>> vector de frecuencias <<<<
        mag  = FR[:, 1]     # >>>> vector de magnitudes  <<<<

    elif opc[:4] == '-fs=':
        if opc[4:] in ('44100', '48000', '96000'):
            fs = int(opc[4:])
        else:
            print "fs debe ser 44100 | 48000 | 96000"
            sys.exit()

    elif opc[:3] == '-e=':
        if opc[3:] in ('13', '14', '15', '16'):
            m = 2**int(opc[3:])
        else:
            print "m: 13...16 (8K...64K taps)"
            sys.exit()

    elif opc[:5] == '-ref=':
        try:
            ref_level = opc[5:]
            ref_level = round( float(ref_level), 1)
            autoRef = False
        except:
            print __doc__
            sys.exit()

    elif opc[:6] == '-scho=':
        try:
            fScho = float(opc[6:])
        except:
            print __doc__
            sys.exit()
            
    elif '-v' in opc:
        verFIRs = True

    else:
        print __doc__
        sys.exit()

# Información
if fs == fs_FRD:
    print "(i) fs=" + str(fs) + " coincide con la indicada en " + FRDname
else:
    print "(i) fs=" + str(fs) +  " distinta de " + str(fs_FRD) + " en " + FRDname

print "(i) Longitud del FIR = " + utils.Ktaps(m)

##########################################################################
# 1 CALCULO DEL TARGET
##########################################################################

# 1.1 NIVEL DE REFERENCIA
# 'rmag' es una curva muy suavizada 1/1oct que usaremos para tomar el nivel de referencia
rmag = smooth(mag, freq, Noct=1)
if autoRef:
    f1_idx = (np.abs(freq - f1)).argmin()
    f2_idx = (np.abs(freq - f2)).argmin()
    # 'r2mag' es un minivector de las magnitudes del rango de referencia:
    r2mag = rmag[ f1_idx : f2_idx ]
    # Vector de pesos auxiliar para calcular el promedio, de longitud como r2mag
    weightslograte = .5
    weights = np.logspace( np.log(1), np.log(weightslograte), len(r2mag) )
    # Calculamos el nivel de referencia
    ref_level = round( np.average( r2mag, weights=weights ), 2)
    print "(i) Nivel de referencia estimado: " +  str(ref_level) + " dB --> 0 dB"
else:
    print "(i) Nivel de referencia: " +  str(ref_level) + " dB --> 0 dB"

# 1.2 TARGET PARA ECUALIZAR
# 'Noct'   suavizado fino inicial en graves (por defecto 1/48 oct)
# 'f0'     freq a la que empezamos a suavizar más hasta llegar a 1/1 oct en Nyquist
# 'Tspeed' velocidad de transición del suavizado audiotools/smoothSpectrum.py
f0 = 2**(-octScho) * fScho
# El target a ecualizar, resultado de suavizar la FRD original
target = smooth(mag, freq, Noct, f0=f0, Tspeed=Tspeed)

# 1.2 Reubicamos las curvas en el nivel de referencia
mag    -= ref_level   # curva de magnitudes original
rmag   -= ref_level   # minicurva de magnitudes para buscar el ref_level
target -= ref_level   # curva target

##########################################################################
# 2 CÁLCULO DE LA EQ
##########################################################################

# 2.1 'eq' es la curva de ecualización por inversión del target:
eq  = -target

# 2.2 recortamos ganacias positivas:
np.clip(eq, a_min=None, a_max=0.0, out=eq)

# 2.3 y limamos asperezas
eq = smooth(eq, freq, Noct=12)

##########################################################################
# 3. Interpolamos para adaptarnos a la longitud 'm' y 'fs'
#    deseados para el impulso del FIR de salida
##########################################################################
if fs <> fs_FRD or m/2 <> len(freq):
    print "(i) Interpolando"
    newFreq, newEq = pydsd.lininterp(freq, eq, m, fs)
else:
    newFreq, newEq = freq, eq

##########################################################################
# 4. Computamos el IR de salida (dom. de la freq --> dom. del tiempo)
##########################################################################

# Preliminares:
# 4.1 Comprobamos que nuestro semiespectro contenga el bin de DC (0 Hz)
if newFreq[0] <> 0:
    print "(i) Insertando el bin 0 Hz"
    newFreq = np.insert(newFreq, 0, 0       )
    newEq =   np.insert(newEq,   0, newEq[0])

# 4.2 Comprobamos que contenga Nyquist
fNyq = fs / 2.0
if round(newFreq[-1] - fNyq, 1)  <> 0.0:
    print "(i) Insertando bin Nyquist", fNyq
    newFreq = np.insert(newFreq, -1, fNyq     )
    newEq =   np.insert(newEq,   -1, newEq[-1])

# 4.3 Y que sea ODD
if len(newEq) % 2 == 0:
    raise ValueError("(!) Algo va mal debería ser un semiespectro ODD con \
                       el primer bin 0 Hz y el último Nyquist") 
    sys.exit()

# 4.4 Traducimos dB --> gain
newEq = 10.0**(newEq/20.0)

# 4.5 Computamos el impulso calculando la IFFT de la curva 'newEq'.
#     OjO nuestra curva semiespectro 'newEq' es una abstracción reducida a magnitudes
#     reales positivas, pero la IFFT necesita un espectro causal (con phase minima)
#     y completo (freqs positivas y negativas)
spectrum = pydsd.minphsp( pydsd.wholespmp(newEq) ) # Ahora ya tiene phase
imp = np.real( np.fft.ifft( spectrum ) )
imp = pydsd.semiblackmanharris(m) * imp[:m]

# Ahora 'imp' tiene una respuesta causal, natural, o sea de phase mínima.

# 4.5 Versión linear-phase (experimental) ...
impLP = utils.MP2LP(imp, windowed=True, kaiserBeta=1)

# 4.6 Guardamos los impulsos en archivos .pcm

# Nombres de los pcm:
ch = 'C' # genérico por si no viene nombrado el frd
if FRDname[0].upper() in ('L','R'):
    ch = FRDname[0].upper()
    resto = FRDname[1:-4].strip().strip('_').strip('-')
mpEQpcmname = str(fs)+'/drc-X-'+ch+'_mp_'+resto+'.pcm'
lpEQpcmname = str(fs)+'/drc-X-'+ch+'_lp_'+resto+'.pcm'

# Guardamos los FIR :
print "(i) Guardando los FIR de ecualización en '" + mpEQpcmname + "' '" + lpEQpcmname + "'"
os.system( 'mkdir -p ' + str(fs) )
utils.savePCM32(imp,   mpEQpcmname)
utils.savePCM32(impLP, lpEQpcmname)

##########################################################################
# 5. PLOTEOS
##########################################################################

# Curva inicial sin suavizar
plt.semilogx(freq, mag,
             label="raw", color="silver", linestyle=":")

# Curva suavizada
plt.semilogx(freq, target,
             label="smoothed", color="blue")

# Cacho de curva usada para calcular el nivel de referencia
if autoRef:
    plt.semilogx(freq[ f1_idx : f2_idx], rmag[ f1_idx : f2_idx ],
                 label="ref level range", color="black", linestyle="--", linewidth=2)

# Curva de EQ
plt.semilogx(freq, eq,
             label="EQ", color="red")

tmp = FRDname + "\n(ref. level @ " + str(ref_level) + " dB --> 0 dB)"
plt.title(tmp)
plt.xlim(20, 20000)
plt.ylim(-30, 10)
plt.grid()
plt.legend()
plt.show()

##########################################################################
# 6. Guardamos las gráficas en un PDF:
##########################################################################
#pdfName = FRDname.replace('.frd', '_eq.pdf').replace('.txt', '_eq.pdf')
#print "\n(i) Guardando gráfica en el archivo " + pdfName
# evitamos los warnings del pdf
# C:\Python27\lib\site-packages\matplotlib\figure.py:1742: UserWarning:
# This figure includes Axes that are not compatible with tight_layout, so
# its results might be incorrect.
import warnings
#warnings.filterwarnings("ignore")
#fig.savefig(pdfName, bbox_inches='tight')

##########################################################################
# 7. Visualización de los FIRs de EQ:
##########################################################################
if verFIRs:
    print "Veamos los FIR con audiotools/IRs_viewer.py ..."
    os.system("IRs_viewer.py '" + lpEQpcmname + "' '" + mpEQpcmname
              + "' 20-20000 -eq -1 " + str(int(fs)))

# FIN
