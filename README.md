Este software permite medir la respuesta 'in room' de unos altavoces y calcular los FIRs para correción de sala **DRC**, mediante el uso de un convolver insertado antes de los altavoces.


## Medición multipunto

El script de medición básico es **`logsweep2TF.py`**. Está basado en el programa Matlab de Richard Mann y John Vanderkooy publicado en el Vol 13 de [linearaudio.net](https://linearaudio.net/downloads), portado a Python/Scipy. Aquí no se trata la respuesta quasi anecoica y otros análisis tratados en dicha publicación.

El script **`roommeasure.py`** permite realizar **_medidas estacionarias en múltiples puntos de micrófono_**, se obtendrá una respuesta promediada en formato `.frd`.

Es responsabilidad del usuario definir la amplitud espacial de las posiciones de micrófono, dependiendo del escenario de escucha.


### Integración con JACK

Para sistemas de altavoces gestionados con JACK, como los disponibles en [AudioHumLab](https://github.com/AudioHumLab), **`roommeasure.py`** dispone de una opción para ordenar el cambio de canal al sistema de altavoces remoto, al objeto de facilitar la automatización de medidas en un sistema estéreo.

![GUI](https://github.com/Rsantct/DRC/blob/master/doc/roommeasure_GUI_screen_1.png)

![GUI](https://github.com/Rsantct/DRC/blob/master/doc/test_sweep.png)



## Cálculo

El script **`roomEQ.py`** se ocupa del cálculo del filtro FIR para DRC a partir de la respuesta `.frd` de arriba, o de cualquier otra obtenida con programas como por ejemplo ARTA o Room EQ Wizard. 

**`roomEQ.py`** permite generar FIR con distintas longitudes (resolucion) y fs.

El nivel de referencia sobre el que se aplica la EQ se estima automaticamente, pero se puede indicar manualmente otro nivel una vez visualizadas las gráficas propuestas por el programa.

```
~$ roomEQ.py 

    roomEQ.py

    Calculates a room equalizer FIR from a given in-room response, usually an
    averaged one as the provided from 'roommeasure.py'.

    Usage:

        roomEQ.py response.frd  [ options ]

            -fs=    Output FIR sampling freq (default 48000 Hz)

            -e=     Exponent 2^XX for FIR length in taps.
                    (default 15, i.e. 2^15=32 Ktaps)

            -ref=   Reference level in dB (default autodetected)

            -scho=  Schroeder freq. (default 200 Hz)

            -wFc=   Gaussian window to limit positive EQ: center freq
                    (default 1000 Hz)

            -wOct=  Gaussian window to limit positive EQ: wide in octaves
                    (default 10 octaves 20 ~ 20 KHz)

            -noPos  Does not allow positive gains at all

            -doFIR  Generates the pcm FIR after estimating the final EQ.

            -plot   FIR visualizer

            -dev    Auxiliary plots

```

![gaps](https://github.com/Rsantct/DRC/blob/master/doc/roomEQ_hard-modes.png)



## Aplicando los FIR

El FIR obtenido debe cargarse en un convolver software como Brutefir en Linux, un plugin de reverb como IR1 de waves en una DAW o un convolver hardware como miniDSP ...

Aquí proponemos las evoluciones **pe.audio.sys** o **pre.di.c**, del proyecto original **FIRtro** (actualmente sin mantenimiento), que se basan en el convolver Brutefir, disponibles en [AudioHumLab](https://github.com/AudioHumLab):

#### https://github.com/AudioHumLab/pe.audio.sys

#### https://github.com/rripio/pre.di.c

#### https://github.com/AudioHumLab/FIRtro/wiki/01---Introducción


## Instalación

### Dependencias

Este software funciona en máquinas Linux o Mac OS (Homebrew), que dispongan de las librerias estandar que se detallan a continuación.

**python3**

    sudo apt install python3-numpy python3-matplotlib python3-scipy

Quizás se necesite actualizar las herramientas de compilación y el gestor de paquetes de Python:

    sudo apt install python3-pip
    sudo apt install build-essential libssl-dev libffi-dev python-dev
    sudo pip3 install --upgrade pip
    sudo pip3 install --upgrade setuptools
    sudo pip3 install sounddevice

**AudioHumLab/audiotools**

También se necesitan las herramientas de audio disponibles en **[AudioHumLab/audiotools](https://github.com/AudioHumLab/audiotools)**

### Instalación 

Para **instalar** este software en el directorio home del usuario

```
cd
wget https://github.com/Rsantct/DRC/archive/master.zip
unzip master
rm master.zip
mv DRC-master DRC
chmod +x DRC/*.py
```

Se recomienda incluir estas utilidades en el PATH del usuario:

```
nano ~/bash_profile
```

```
### AUDIOTOOLS y DRC
export PATH=~/audiotools:~/DRC:$PATH
```

### Actualización

```
sh ~/DRC/update.sh
```  
 
