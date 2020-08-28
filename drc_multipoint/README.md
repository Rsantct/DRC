## DRC multipunto

Se trata de procesar una respuesta promedio de medir en varios puntos, previamente preparada, y generar un FIR para DRC (Digital Room Correction).

Tomar las distintas medidas en distintos puntos de una zona de escucha amplia entorno al punto de escucha previsto.

 

### Respuesta promediada con `roommeasure.py`:

Ejecutar `roommeasure.py` para realizar varias medidas automáticamente y guardar la respuestra promediada en un archivo `.frd`


### Alternativa: respuesta promediada midiendo con ARTA:

1.- Realizar varias medidas IR y promediar la FR, o bien usar el RTA (esto no está probado).

2.- Exportar a `.frd`


### Cálculo de la ecualización `roomEQ.py`:

`roomEQ.py` procesa un archivo de respuesta `Ch_xxxxxx.frd` proporcionado por `roommeasure.py` o por ejemplo por ARTA, y genera los FIRs para ecualizar dicha respuesta.


-------------------------------------------------------

### Procedimiento alternativo con REW - Room EQ Wizard:

#### Obtención de la respuesta promediada:

1.- Tomar varias medidas de IR en distintos puntos de una zona de escucha amplia.

Veremos que los picos modales y los dips de cancelaciones varían mucho. 

Anotar los modos detectados por REW en cada IR medido.
 
2.- Obtener la FR_avg promedio de las medidas anteriores.
 
#### Cálculo de la ecualización con filtros paramétricos:

3.- Calcular filtros para EQ de la FR_avg.
 
Descartar los filtros que no correspondan a los modos más importantes obtenidos arriba.
 
4.- Exportar los parámetros de los filtros EQ finales en un archivo `.txt`
 
#### Herramienta `rew2fir.py`

Procesa un archivo parametricos.txt obtenido con REW.
 
Genera FIRs con los parámetros de los filtros obtenidos con REW.

