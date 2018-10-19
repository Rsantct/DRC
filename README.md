Este software permite medir la respuesta 'in room' y calcular FIRs para correción de sala 'DRC'.

## Medición

El script de medición básico es **`logsweep2TF/logsweep2TF.py`**. Está basado en el programa Matlab publicado por Richard Mann y John Vanderkooy en [linearaudio.net](https://linearaudio.net/downloads), portado a Python/Scipy. Aquí no se trata la respuesta quasi anecoica y otros análisis tratados en dicha publicación.

El script **`drc_multipoint/roommeasure.py`** permite realizar **_medidas estacionarias en múltiples puntos de micrófono_**, se obtendrá una respuesta promediada en formato `.frd`.

Es responsabilidad del usuario definir la amplitud espacial de las posiciones de micrófono, dependiendo del escenario de escucha.

## Cálculo

El script **`drc_multipoint/roomEQ.py`** se ocupa del cálculo del filtro de eq DRC a partir de la respuesta `.frd` de arriba, o de cualquier otra obtenida con programas como por ejemplo ARTA o Room EQ Wizard. Proporciona filtros minimum phase y linear phase, ambos con idéntica respuesta en magnitud.

Emmo, la variante `mp` puede resultar más adecuada en escenarios 'near field' con punto de escucha muy localizado. Los accidentes en la respuesta en frecuencia por debajo de la frecuencia de Shroeder en esa localización de escucha tendrán una naturaleza minimum phase invariable, entonces la corrección `mp` será óptima. Esta variante no introduce latencia.

La variante `lp` puede adaptarse mejor a escenarios 'mid field' tipo Hi-Fi doméstica con posiciones de escucha más variables. En este escenario es difícilmente precedecible una corrección en amplitud y su fase mínima asociada. Para calcular el filtro de drc, podremos confeccionar la respuesta `.frd` promediando varias medidas tomadas en un amplio espacio de posiciones de micrófono.

**`roomEQ.py`** permite generar FIR con distintas longitudes (resolucion) y fs. El nivel de referencia sobre el que se aplica la EQ se estima automaticamente, pero se puede indicar manualmente otro nivel una vez vista la propuesta del programa:

```
~$ roomEQ.py 

    roomEQ.py

    Calcula un FIR para ecualizar la respuesta de una sala.

    Uso:
        python roomEQ.py respuesta.frd  -fs=xxxxx  [ -ref=XX  -scho=XX e=XX -v ]

        -fs=    fs del FIR de salida, por defecto 48000 (Hz)
        -e=     Longitud del FIR en taps 2^XX. Por defecto 2^15, es decir,
                32 Ktaps con resolución de 16K bins sobre la fs.

        -ref=   Nivel de referencia en XX dB (autodetectado por defecto)
        -scho=  Frecuencia de Schroeder (por defecto 200 Hz)
        -nofir  Solo se estima el target y la eq, no genera FIRs

        -v      Visualiza los impulsos FIR generados

        -dev    Gráficas auxiliares sobre la EQ

    Se necesita  github.com/AudioHumLab/audiotools
```
![graph](https://github.com/Rsantct/DRC/blob/master/drc_multipoint/roomEQ_drc.png =640x480)


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
chmod +x DRC/logsweep2TF/*.py
chmod +x DRC/drc_multipoint/*.py
chmod +x DRC/drc_multipoint/*.sh
```

Se recomienda incluir estas utilidades en el PATH del usuario:

```
nano ~/bash_profile
```

```
### AUDIOTOOLS y DRC
export PATH=~/audiotools:~/DRC/logsweep2TF:~/DRC/drc_multipoint:$PATH
```

## Actualización

```
sh ~/DRC/update.sh
```  
 
