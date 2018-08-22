# Experimento: DRC usando filtros linear-phase
 
## https://www.roomeqwizard.com/help/help_en-GB/html/minimumphase.html
 
Las reflexiones producen regiones phase-excess NO reversibles con EQ min-phase.
 
La FR de la una respuesta in room es mixed-phase, hay regiones min-ph y otras que no. En general, las regiones min-ph tienden a mantenerse en las frecuencias inferiores, pero no siempre es así.
 
Dada una curva de una medida de FR no plana, deberemos comparar la phase de medida con la minimum phase teórica que corresponde a la FR medida, o sea extraer el excess phase. Entonces podremos analizar el GD del exceso de phase 'EGD' y podremos identificar las zonas con EGD constante como zonas minumum phase de nuestro sistema.
 
Aquellas regiones de graves en las que vemos discontinuidades en EGD se corresponderán con DIPS por cancelaciones. NO SON ECUALIZABLES.
 
Las regiones de los graves con picos magnitud, normalmente se corresponden con room modes y son min-ph con EGD constante. En general los picos de magnitud en una FR, son debidos a polos de la función de transferencia del sistema y por tanto pueden cancelarse añadiendo zeros con un EQ.
 
También encontraremos regiones en frecuencias medias con EGD constante por tanto son min-pha, como de 300 - 500 Hz, a pesar de las fuertes variaciones de magnitud que pueda haber. Peeeero ya estamos en unas medidas de magnitud muy dependientes de la posición del micrófono ya que las semilongitudes de onda aquí ya son de pocos centímetros.
 
Como norma general NO debe emplearse narrow BW EQ fuera del rango modal. Al subir la frecuencia, debemos incrementar el BW de la EQ.
 
## El experimento:
 
En general se asume que los problemas modales de una sala son fenómenos de minumum-phase y por tanto son ecualizables con filtros convencionales minumum-phase.
 
En mi opinión, esto es cierto para un punto de escucha determinado y no ocurrirá en otros cercanos.
 
En este experimento elegimos una EQ linear-phase, simplemente queremos atenuar aquellos "boom" modales que son tan molestos y que predominan en una zona de escucha amplia.
 
El resultado esperado es que al no usar una EQ que modifica la phase en graves, además de librarnos de los "booms" de la sala, deberíamos percibir un grave más coherente.

El principal problema de esta solución es el alto retardo inherente a usar FIRs largos de alta resolución, no apto para la escucha de material audiovisual.

## El procedimiento:
 
**Herramienta: REW Room EQ Wizard**
 
1. Tomar varias medidas de IR en distintos puntos de la sala.
 
    Anotar los modos detectados por REW en casa IR.
 
2. Obtener la FR_avg promedio de las medidas anteriores.
 
3. Calcular filtros para EQ de la FR_avg.
 
    Descartar los filtros que no correspondan a los modos más importantes obtenidos en 1.
 
4. Exportar los parámetros de los filtros EQ finales.
 
**Herramienta: [audiotools/docs/DRC/peq2fir.py](https://github.com/Rsantct/audiotools/blob/testing/docs/DRC/peq2fir.py)**
 
5. Generar FIRs linear-phase con los parámetros de los filtros obtenidos con REW.
 
**Herramienta: FIRtro**
 
6. Cargar el FIR de arriba en la etapa drc_fir de FIRtro
 
7. Evaluar el resultado.

## El resultado

COMING SOON ... ...
