Este software permite medir la respuesta 'in room' y calcular FIRs para correción de sala 'DRC'.

## Medición

El script de medición básico es **`logsweep2TF/logsweep2TF.py`**. Está basado en el programa Matlab publicado por Richard Mann y John Vanderkooy en [linearaudio.net](https://linearaudio.net/downloads), portado a Python/Scipy. Aquí no se trata la respuesta quasi anecoica y otros análisis tratados en dicha publicación.

El script **`drc_multipoint/roommeasure.py`** permite realizar medidas estacionarias en múltiples puntos de micrófono, se obtendrá una respuesta promediada en formato `.frd`.

Es responsabilidad del usuario definir la amplitud espacial de las posiciones de micrófono, dependiendo del escenario de escucha.

## Cálculo

El script **`drc_multipoint/roomEQ.py`** se ocupa del cálculo del filtro de eq DRC a partir de la respuesta `.frd` de arriba, o de cualquier otra obtenida con programas como por ejemplo ARTA o Room EQ Wizard. Proporciona filtros minimum phase y linear phase, ambos con idéntica respuesta en magnitud.

Emmo, la variante `mp` puede resultar más adecuada en escenarios 'near field' con punto de escucha muy localizado. Los accidentes en la respuesta en frecuencia por debajo de la frecuencia de Shroeder en esa localización de escucha tendrán una naturaleza minimum phase invariable, entonces la corrección `mp` será óptima. Esta variante no introduce latencia.

La variante `lp` puede adaptarse mejor a escenarios 'mid field' tipo Hi-Fi doméstica con posiciones de escucha más variables. En este escenario es difícilmente precedecible una corrección en amplitud y su fase mínima asociada. Para calcular el filtro de drc, podremos confeccionar la `frd` promediando varias medidas tomadas en un amplio espacio de posiciones de micrófono.

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
export PATH=~/audiotools:~/DRC/logsweep2TF:~/DRC/drc_linpha:$PATH
```

## Actualización

```
sh ~/DRC/update.sh
```  
 
