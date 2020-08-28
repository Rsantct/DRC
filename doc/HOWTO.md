## 1. Preparar equipo de medición:

PC portátil, tarjeta de sonido USB, micrófono y cables.


## 2. Preparar los altavoces:

- Sin ecualizaciones (loudness, tonos, drc, etc)
- Ajustar un volumen prudente
- Seleccionar la input analógica

## 3. Verificar niveles en la tarjeta de sonido y en altavoces.

Elegir los dispositivos de sonido de entre los mostrados por 

    $ logsweep2TF.py -h

        SYSTEM SOUND DEVICES:

    > 0 Built-in Microphone, Core Audio (2 in, 0 out)
    < 1 Built-in Output, Core Audio (0 in, 2 out)
      2 USB Audio CODEC , Core Audio (0 in, 2 out)
      3 USB Audio CODEC , Core Audio (2 in, 0 out)

En este ejemplo usaremos el `3` para captura y el `2` para playback.

Insertar el micro en la entrada 'Left/1' de la tarjeta de sonido.

Se prefiere equipar la tarjeta con un cable en Y en la salida 'Left/1' que servirá de salida hacia el amplificador y de loop hacia la entrada de referencia 'Right/2'. Esto es opcional, el programa puede funcionar sin señal en el canal de entrada de referencia.

**Probar niveles**, señal capturada y longitud del sweep para que no haya clipping ni falta de 'time clearance' (se avisa en el terminal). Por ejemplo:

    $ logsweep2TF.py -dev=3,2,48000 -e17

Ejecutarlo sucesivamente, ajustar volumen del altavoz y ajustar en la tarjeta de sonido niveles de salida y de entrada (micro y loop), **verificando** que:

- El nivel SPL en punto de escucha es suficientemente alto.

- Los indicadores de clipping de la tarjeta de sonido no se encienden durante el sweep, en ninguno de los canales (micro y bucle de referencia).

- El nivel de la señal de la entrada 'Left' es alto (ver gráfica azul del sweep capturado), PERO no alcanza -3dB (esto se observa el el terminal). Lo mismo para el canal de referencia.

- Los sweeps grabados se muestran uniformes sin discontinuidades.

- El sweep capturado en el canal de referencia no muestra compresión (saturación).

Más detalles aqui: **https://github.com/Rsantct/DRC/tree/master/logsweep2TF**  



## 4. Replantear las posiciones de micro que queremos cubrir.

Se recomienda cubrir posiciones en distintas alturas de micro, a criterio del usuario.

Para escuchas en campo cercano o en un punto de escucha definido, podemos medir en varias posiciones no demasiado alejadas para centrar la corrección en los fenómenos acústicos que ocurren en dicha posición de escucha.

Para una ecualización generalista 'que se oiga bien en toda la sala' podemos medir en posiciones más repartidas ...

Recordemos que un buen resultado DRC depende de disponer de

- unos altavoces con una buena ecualización en campo libre.

- una sala mínimamente tratada acústicamente.

- una posición de escucha bien elegida dentro de la distribución modal y de reflexiones de la sala.


## 5. Medir.
    
Se recomienda `-e18`, la S/N ratio y el 'time clearance' serán mejores que con `-e17`.

Por ejemplo mediremos en 7 posiciones de micro e intercalando las medidas de los altavoces izquierdo y derecho con la opción `-cLR`, por lo que deberemos cambiar el canal de entrada al sistema a medida que se nos indique por el terminal:

    $ roommeasure.py -dev=3,2,48000 -e18 -cLR -m7

Para cambiar entre el canal L y R podemos hacerlo a mano (o con un script para sistemas basados en FIRtro).

Obtenderemos respuestas promedio:

    xxxx_avg.frd

y, a nivel informativo, unas respuestas suavizadas de la respuesta estacionaria:

    xxxx_avg_smooth.frd

Se mostrarán gráficas de las curvas medidas.

Más adelante podremos revisarlas:

- Curvas raw en cada punto: `FRD_tool.py   $(ls L_room_?.frd)`

- Curvas suavizadas en cada punto: `FRD_tool.py   $(ls L_room_?.frd)  -f0=200  -12oct`

- Curva promedio de todos los puntos: `FRD_tool.py   L_room_avg.frd   L_room_avg_smoothed.frd`

## 6. Generar los filtros de ecualización DRC

Ejecutaremos el programa para cada canal e indicando la Fs de trabajo de nuestro convolver.

    roomEQ.py L_room_avg.frd -fs=44100
    roomEQ.py R_room_avg.frd -fs=44100
    
Se generará una carpeta con un juego en minimum phase (mp) y otro experimental en linear phase (lp).

    $ ls 44100_32Ktaps/
    drc.L.lp.pcm  drc.L.mp.pcm drc.R.lp.pcm  drc.R.mp.pcm
    $ 


Podemos visulizar estos IR (impulse response) con su respuesta en frecuencia y retardo de grupo:

    IRs_viewer.py drc.L.mp.pcm drc.L.lp.pcm 44100 -eq -1
    

## 7. Llevar los filtros al convolver

### Ejemplo para un sistema de altavoces basado en **FIRtro**

Subimos los FIR pcm al sistema, en este caso **[pe.audio.sys](https://github.com/AudioHumLab/pe.audio.sys)**:
    
    echo "put drc*" | sftp myUser@myFIRtroIP
    
Y actualizamos el convolver para usarlos:

    $ ssh myUser@myFIRtroIP
    $ cd

    # Reubicamos los .pcm en la carpeta de nuestro altavoz, con un nombre conveniente:
    $ mv drc.L.mp.pcm pe.audio.sys/loudspeakers/miAltavoz/drc.L.sofa_mp.pcm
    $ mv drc.R.mp.pcm pe.audio.sys/loudspeakers/miAltavoz/drc.R.sofa_mp.pcm
    $ mv drc.L.lp.pcm pe.audio.sys/loudspeakers/miAltavoz/drc.L.sofa_lp.pcm
    $ mv drc.R.lp.pcm pe.audio.sys/loudspeakers/miAltavoz/drc.R.sofa_lp.pcm
    
    # Editamos el convolver para que pueda usarlos:
    $ nano pe.audio.sys/loudspeakers/miAltavoz/brutefir_config
    
    # reiniciamos el sistema
    $ peaudiosys_restart.sh
    
    # comprobamos
    $ control get_drc_sets
    ["equilat_lp", "sofa_lp", "equilat_mp", "sofa_mp"]


### Caso de una DAW

Para ecualizar la salida de una DAW hacia un sistema de monitores de campo cercano, necesitamos insertar un plugin de reverb en el bus de salida a monitores de la DAW.

En caso que el formato requerido por el plugin sea WAV stereo, podemos convertir nuestros archivos .pcm a .wav con la herramienta SoX:

    1) hacemos copias de los .pcm para tener la extension .f32 que necesita SoX

    $ cp drc.L.mp.pcm drc.L.mp.f32
    $ cp drc.R.mp.pcm drc.R.mp.f32

    2) usamos el comando -m (mix) de SoX, deberemos indicar la Fs del filtro FIR, por ejemplo:

    $ sox  -m       -c 1 -r 44100 drc.L.mp.f32  -c 1 -r 44100 drc.R.mp.f32  -c 2 -b 16 drc.mp.wav
           (mix)    (primer stream)             (segundo stream)            (stream de salida)




