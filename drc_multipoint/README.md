# DRC multipunto

Se trata de procesar una respuesta promedio de medir en varios puntos, previamente preparada, y generar un FIR para DRC (Digital Room Correction).

Tomar las distintas medidas en distintos puntos de una zona de escucha amplia entorno al punto de escucha previsto.


## Procedimiento de EQ con `roomEQ.py`:
 

### Respuesta promediada con `logsweep2TF/roommeasure.py`:

Ejecutar `roommeasure.py` para realizar varias medidas automáticamente y guardar la respuestra promediada en un archivo `.frd`


### Alternativa: respuesta promediada midiendo con ARTA:

1.- Realizar varias medidas IR y promediar la FR, o bien usar el RTA (esto no está probado).

2.- Exportar a `.frd`


### Cálculo de la EQ con roomEQ.py

- Procesa un archivo `Ch_xxxxxx.frd` por ejemplo de de ARTA o de `roommeasure.py`.
 
- Genera FIRs para ecualizar la respuesta .frd

Nota: **roomEQ.py** proporciona FIRs en versiones minimum-phase y linear-phase (experimental)



## Procedimiento alternativo con REW - Room EQ Wizard:
 
1.- Tomar varias medidas de IR en distintos puntos de una zona de escucha amplia.

Veremos que los picos modales y los dips de cancelaciones varían mucho. 

Anotar los modos detectados por REW en cada IR medido.
 
2.- Obtener la FR_avg promedio de las medidas anteriores.
 
3.- Calcular filtros para EQ de la FR_avg.
 
Descartar los filtros que no correspondan a los modos más importantes obtenidos arriba.
 
4.- Exportar los parámetros de los filtros EQ finales en un archivo `.txt`
 
### Herramienta `rew2fir.py`

Procesa un archivo parametricos.txt obtenido con REW.
 
Genera FIRs con los parámetros de los filtros obtenidos con REW.

Nota: **rew2fir.py** proporciona FIRs en versiones minimum-phase y linear-phase (experimental)


## Aplicando los FIR de DRC

El FIR obtenido debe cargarse en un convolver software como Brutefir en Linux, un plugin de reverb como IR1 de waves en una DAW o un convolver hardware como miniDSP ...

Aquí proponemos las evoluciones **pe.audio.sys** o **pre.di.c** del proyecto original **FIRtro** (actualmente sin mantenimiento), basadas en Brutefir.

**https://github.com/AudioHumLab/pe.audio.sys**

**https://github.com/rripio/pre.di.c**

**https://github.com/AudioHumLab/FIRtro/wiki/01---Introducción**



## ==================( experimental )========================

### DRC usando filtros linear-phase
 
#### Intro

https://www.roomeqwizard.com/help/help_en-GB/html/minimumphase.html
 
La FR de la una respuesta in room es mixed-phase, hay regiones min-ph y otras que no. En general, las regiones min-ph tienden a mantenerse en las frecuencias inferiores, pero no siempre es así.
 
Por ejemplo, las reflexiones producen regiones phase-excess NO reversibles con EQ min-phase.
 
¿Cómo identificar regiones min-phase ecualizables?.

Dada una curva de una medida de FR no plana, deberemos comparar la phase de medida con la minimum phase teórica que corresponde a la FR medida, o sea: extraer el excess phase. Entonces podremos analizar el GD del exceso de phase 'EGD' y podremos identificar las zonas con EGD constante como zonas minumum phase de nuestro sistema.
 
Aquellas regiones de graves en las que vemos discontinuidades en EGD se corresponderán con DIPS por cancelaciones. NO SON ECUALIZABLES.
 
Las regiones de los graves con picos magnitud, normalmente se corresponden con room modes y son minimum-phase con EGD constante. En general los picos de magnitud en una FR, son debidos a polos de la función de transferencia del sistema y por tanto pueden cancelarse añadiendo zeros con un EQ.
 
Como norma general NO debe emplearse narrow BW EQ fuera del rango modal. Al subir la frecuencia, debemos incrementar el BW de la EQ.
 
También encontraremos regiones en frecuencias medias con EGD constante por tanto son min-pha, como de 300 - 500 Hz, a pesar de las fuertes variaciones de magnitud que pueda haber. Peeeero ya estamos en unas medidas de magnitud muy dependientes de la posición del micrófono ya que las semilongitudes de onda aquí ya son de pocos centímetros.
 
#### El experimento:
 
En general se asume que los problemas modales de una sala son fenómenos de minumum-phase y por tanto son ecualizables con filtros convencionales minumum-phase.
 
En mi opinión, esto es cierto para un punto de escucha determinado y no ocurrirá en otros cercanos.
 
A modo experimental podemos probar una EQ linear-phase, simplemente queremos atenuar aquellos "boom" modales que son tan molestos y que predominan en una zona de escucha amplia.
 
El resultado esperado es que al no usar una EQ que modifica la phase en graves, además de librarnos de los "booms" de la sala, deberíamos percibir un grave más coherente.

El principal problema de esta solución es el alto retardo inherente de los FIRs lin-phase y de alta resolución (largos), no apto para la escucha de material audiovisual. Entonces conviene aplicar EQ convenvional min-phase. Puede ser FIR en un convolver como Brutefir (FIRtro). O puede ser IIR, entonces consumiremos menos CPU (un host como Ecasound con plugins DSP también disponible en FIRtro).




