Este software permite medir la respuesta 'in room' y calcular FIRs para correción de sala 'DRC'.

## Medición

El script de medición básico es **`logsweep2TF.py`**. Está basado en el programa Matlab publicado por Richard Mann y John Vanderkooy en [linearaudio.net](https://linearaudio.net/downloads), portado a Python/Scipy. Aquí no se trata la respuesta quasi anecoica y otros análisis tratados en dicha publicación.

El script **`roommeasure.py`** permite realizar medidas estacionarias en múltiples puntos de micrófono, y obtendrá una respuesta promediada en formato `.frd`.

Es responsabilidad del usuario definir la amplitud espacial de las posiciones de micrófono, dependiendo del escenario de escucha.

## Cálculo

El script **`roomEQ.py`** se ocupa del cálculo del filtro de eq DRC a partir de la respuesta `.frd` de arriba, o de cualquier otra obtenida con programas como por ejemplo ARTA, etc.. Proporciona filtros minimum phase y linear phase, ambos con idéntica respuesta en magnitud.

Emmo, la variante `mp`puede resultar más adecuada en escenarios 'near field' con punto de escucha muy estable. Los accidentes en la respuesta en frecuencia por debajo de la frec. de Shroeder en estas condiciones tendrán naturaleza minimum phase y la corrección mp será entonces la óptima. Esta variante no introduce latencia.

La variante `lp` puede adaptarse mejor a escenarios 'mid field' tipo Hi-Fi doméstica con más influencia del campo reverberante y con posiciones de escucha más variables, si se confecciona a partir de una medida promediada en un amplio espacio de posiciones de micrófono.

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
chmod +x DRC/drc_linpha/*.py
chmod +x DRC/logsweep2TF/*.sh
chmod +x DRC/drc_linpha/*.sh
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
 
