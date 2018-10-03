# DRC

Genera FIRs para correción de sala DRC.

El software tiene dos partes: medición y cálculo de filtros DRC.

## Medición

El script de medición básico es **`logsweep2TF.py`**. Está basado en el programa Matlab publicado por Richard Mann y John Vanderkooy en [linearaudio.net](https://linearaudio.net/downloads), portado a Python/Scipy.

El script **`roommeasure.py`** permite realizar medidas estacionarias en múltiples puntos de micrófono, y obtendrá una respuesta promediada en formato `.frd`.

Es responsabiidad del usuario definir la amplitud espacial de las posiciones de micrófono, dependiendo del escenario de escucha.

## Cálculo

El script **`roomEQ.py`** se ocupa del cálculo del filtro de eq DRC a partir de la respuesta `.frd` de arriba, o de cualquier otra obtenida con programas como por ejemplo ARTA, etc.. Proporciona filtros minimum phase y linear phase, ambos con idéntica respuesta en magnitud.

Emmo, la variante `mp`puede resultar más adecuada en escenarios 'near field' con punto de escucha muy estable. Esta variante no introduce latencia.

La variante `lp` puede adaptarse mejor a escenarios mid field tipo Hi-Fi con más influencia de campo reverberante y con posiciones de escucha más variables, si se confecciona a partir de una medida promediada en un amplio espacio de posiciones de micrófono.


## Instalación

### Dependencias

Este software necesita:

- **Python: numpy, scipy, matplotlib**

- **https://github.com/AudioHumLab/audiotools**


Para **instalar** este software en el home del usuario

  ```
  cd
  wget https://github.com/Rsantct/DRC/archive/master.zip
  unzip master
  rm master.zip
  mv DRC-master DRC
  ```

Se recomienda incluir estas utilidades en el PATH del usuario:

  ```
  nano ~/bash_profile
  ```

  ```
  ### AUDIOTOOLS y DRC
  export PATH=~/bin:~/audiotools:${PATH}
  export PATH=~/bin:~/DRC/logsweep2TF:${PATH}
  export PATH=~/bin:~/DRC/drc_linpha:${PATH}
  ```

## Actualización

  ```
  sh ~/DRC/update.sh
  ```  
 
