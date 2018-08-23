# Experimento: DRC usando filtros linear-phase
 
## Intro

https://www.roomeqwizard.com/help/help_en-GB/html/minimumphase.html
 
La FR de la una respuesta in room es mixed-phase, hay regiones min-ph y otras que no. En general, las regiones min-ph tienden a mantenerse en las frecuencias inferiores, pero no siempre es así.
 
Por ejemplo, las reflexiones producen regiones phase-excess NO reversibles con EQ min-phase.
 
¿Cómo identificar regiones min-phase ecualizables?.

Dada una curva de una medida de FR no plana, deberemos comparar la phase de medida con la minimum phase teórica que corresponde a la FR medida, o sea: extraer el excess phase. Entonces podremos analizar el GD del exceso de phase 'EGD' y podremos identificar las zonas con EGD constante como zonas minumum phase de nuestro sistema.
 
Aquellas regiones de graves en las que vemos discontinuidades en EGD se corresponderán con DIPS por cancelaciones. NO SON ECUALIZABLES.
 
Las regiones de los graves con picos magnitud, normalmente se corresponden con room modes y son min-ph con EGD constante. En general los picos de magnitud en una FR, son debidos a polos de la función de transferencia del sistema y por tanto pueden cancelarse añadiendo zeros con un EQ.
 
Como norma general NO debe emplearse narrow BW EQ fuera del rango modal. Al subir la frecuencia, debemos incrementar el BW de la EQ.
 
También encontraremos regiones en frecuencias medias con EGD constante por tanto son min-pha, como de 300 - 500 Hz, a pesar de las fuertes variaciones de magnitud que pueda haber. Peeeero ya estamos en unas medidas de magnitud muy dependientes de la posición del micrófono ya que las semilongitudes de onda aquí ya son de pocos centímetros.
 
## El experimento:
 
En general se asume que los problemas modales de una sala son fenómenos de minumum-phase y por tanto son ecualizables con filtros convencionales minumum-phase.
 
En mi opinión, esto es cierto para un punto de escucha determinado y no ocurrirá en otros cercanos.
 
En este experimento elegimos una EQ linear-phase, simplemente queremos atenuar aquellos "boom" modales que son tan molestos y que predominan en una zona de escucha amplia.
 
El resultado esperado es que al no usar una EQ que modifica la phase en graves, además de librarnos de los "booms" de la sala, deberíamos percibir un grave más coherente.

El principal problema de esta solución es el alto retardo inherente de los FIRs lin-phase y de de alta resolución (largos), no apto para la escucha de material audiovisual. Entonces conviene aplicar EQ convenvional min-phase. Puede ser FIR en un convolver como Brutefir (FIRtro). O puede ser IIR, entonces consumiremos menos CPU (un host como Ecasound con plugins DSP).

## El procedimiento:
 
**Herramienta: REW Room EQ Wizard**
 
1. Tomar varias medidas de IR en distintos puntos de la sala.
 
    Anotar los modos detectados por REW en casa IR.
 
2. Obtener la FR_avg promedio de las medidas anteriores.
 
3. Calcular filtros para EQ de la FR_avg.
 
    Descartar los filtros que no correspondan a los modos más importantes obtenidos en 1.
 
4. Exportar los parámetros de los filtros EQ finales.
 
**[Herramienta: rew2fir.py](https://github.com/Rsantct/DRC/blob/master/drc_lin-pha/rew2fir.py)**
 
5. Generar FIRs linear-phase con los parámetros de los filtros obtenidos con REW. Nota: **rew2fir.py** proporciona ambas versiones minimum-phase y linear-phase.
 
**Herramienta: FIRtro**
 
6. Cargar el FIR de arriba en la etapa drc_fir de FIRtro
 
7. Evaluar el resultado.

## El resultado

En una primera prueba los nuevos filtros FIR construidos a partir de paramétricos funcionan correctamente, no se observan artifactos.

FIRtro permite elegir entre:
- DRC_FIR con estos filtros mp/lp .pcm
- DRC_IIR (plugins ecasound) con los parámetricos. Se observa que el resultado "matamodos" es equivalente.

La variante lp introduce un retardo de unos 370ms respecto de la mp, como era de esperar con 32Ktaps@44100.

Los graves ecualizados con la variante linear-phase comentada aquí aparentan la mejora en coherencia pretendida. Queda pendiente un periodo de pruebas más extenso ;-)







