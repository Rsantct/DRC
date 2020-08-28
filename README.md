Este software permite medir la respuesta 'in room' y calcular FIRs para correción de sala 'DRC'.


## Medición

El script de medición básico es **`logsweep2TF.py`**. Está basado en el programa Matlab publicado por Richard Mann y John Vanderkooy en [linearaudio.net](https://linearaudio.net/downloads), portado a Python/Scipy. Aquí no se trata la respuesta quasi anecoica y otros análisis tratados en dicha publicación.

El script **`roommeasure.py`** permite realizar **_medidas estacionarias en múltiples puntos de micrófono_**, se obtendrá una respuesta promediada en formato `.frd`.

Es responsabilidad del usuario definir la amplitud espacial de las posiciones de micrófono, dependiendo del escenario de escucha.

## Cálculo

El script **`roomEQ.py`** se ocupa del cálculo del filtro FIR para DRC a partir de la respuesta `.frd` de arriba, o de cualquier otra obtenida con programas como por ejemplo ARTA o Room EQ Wizard. 

**`roomEQ.py`** permite generar FIR con distintas longitudes (resolucion) y fs. El nivel de referencia sobre el que se aplica la EQ se estima automaticamente, pero se puede indicar manualmente otro nivel una vez vista la propuesta del programa:


[ CAPTURA COMMAND LINE ]

[ CAPTURA PLOTS]


## Aplicando los FIR de DRC

El FIR obtenido debe cargarse en un convolver software como Brutefir en Linux, un plugin de reverb como IR1 de waves en una DAW o un convolver hardware como miniDSP ...

Aquí proponemos las evoluciones **pe.audio.sys** o **pre.di.c** del proyecto original **FIRtro** (actualmente sin mantenimiento), basadas en Brutefir.

**https://github.com/AudioHumLab/pe.audio.sys**

**https://github.com/rripio/pre.di.c**

**https://github.com/AudioHumLab/FIRtro/wiki/01---Introducción**



## Instalación

### Dependencias

Este software necesita:

- **Python: numpy, scipy, matplotlib, sounddevice**

Quizás se necesite actualizar las herramientas de compilación y el gestor de paquetes de Python:
```
sudo apt-get install build-essential libssl-dev libffi-dev python-dev
sudo pip install --upgrade pip
sudo pip install --upgrade setuptools
sudo pip install sounddevice
```

- **https://github.com/AudioHumLab/audiotools**


Para **instalar** este software en el home del usuario

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

## Actualización

```
sh ~/DRC/update.sh
```  
 
