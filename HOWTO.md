# Cómo preparar filtros `drc_linpha` de DRC para FIRtro.

## 1. Preparar equipo de medición: PC portátil, tarjeta de sonido USB, micrófono y cables.

Preparar el software de medición y ecualización, según de indica en:

**https://github.com/Rsantct/DRC**  

## 2. Preparar FIRtro

- Sin EQs (drc, peq, loudness, tonos)
- Ajustar un nivel prudente p.ej -10 dBFS
- Seleccionar la input analógica


## 3. Verificar niveles en la tarjeta de sonido y en altavoces.

Elegir los dispositivos de sonido de entre los mostrados por 

    logsweep2TF.py -h

        SYSTEM SOUND DEVICES:

    > 0 Built-in Microphone, Core Audio (2 in, 0 out)
    < 1 Built-in Output, Core Audio (0 in, 2 out)
      2 USB Audio CODEC , Core Audio (0 in, 2 out)
      3 USB Audio CODEC , Core Audio (2 in, 0 out)

En este ejemplo usaremos el `2` para captura y el `3` para playback.

Insertar el micro en la entrada 'Left/1' de la tarjeta de sonido.

Se prefiere equipar la tarjeta con un cable en Y en la salida 'Left/1' que servirá
de salida hacia el amplificador y de loop hacia la entrada de referencia 'Right/2'.

**Probar niveles**, señal capturada y longitud del sweep para que no haya
clipping ni falta de 'time clearance' (se avisa en el terminal). Por ejemplo:

    logsweep2TF.py -dev=3,2,48000 -e17

Ejecutarlo sucesivamente, ajustar volumen de FIRtro y ajustar en la tarjeta de sonido niveles de salida y de entrada (micro y loop), **verificando** que:

- El nivel SPL en punto de escucha es suficientemente alto.

- Los indicadores de clipping de la tarjeta de sonido no se encienden durante el sweep,
  en ninguno de los canales (micro y bucle de referencia).

- El nivel de la señal de la entrada 'Left' es alto (ver gráfica azul del sweep capturado),
  PERO no alcanza -3dB (esto se observa el el terminal). Lo mismo para el canal de referencia.

- Los sweeps grabados se muestran uniformes sin discontinuidades.

- El sweep capturado en el canal de referencia no muestra compresión (saturación).


## 4. Replantear las posiciones de micro que queremos cubrir.

Se recomienda cubrir posiciones en distintas alturas de micro.


## 5. Medir.
    
Se recomienda `-e18`, la S/N ratio y el 'time clearance' serán mejores que con `-e17`.

Por ejemplo mediremos en 7 posiciones de micro e intercalando las medidas de los altavoces
izquierdo y derecho con la opción `-cLR`, por lo que deberemos cambiar el canal de entrada al sistema
a medida que se nos indique por el terminal:

    roommeasure.py -dev=3,2,48000 -e18 -cLR -m7

Para cambiar el canal de entrada al sistema podemos dejar el cable en la entrada
analógica izquierda e ir conmutando con ayuda del script `bin_custom/prueba_canal`
en otro terminal accesorio conectado a FIRtro por ssh.

Obtenderemos respuestas promedio:

    xxxx_avg.frd

y, a nivel informativo, unas respuestas suavizadas de la respuesta estacionaria:

    xxxx_avg_smooth.frd

## 4. Generar los filtros de ecualización DRC, para cada canal.

    roomEQ.py L_room_avg.frd 44100
    roomEQ.py R_room_avg.frd 44100
    
Se generará un juego en minimum phase (mp) y otro en linear phase (lp).

    $ ls drc*
    drc-X-L_lp_room_avg.pcm
    drc-X-R_lp_room_avg.pcm
    drc-X-L_mp_room_avg.pcm
    drc-X-R_mp_room_avg.pcm
    
## 5. Llevar los filtros a FIRtro

Si ya tenemos otros juegos, por ejemplo drc-1-... drc-2-... y drc-3... ,
  querremos que los nuestros sean numerados desde 4
      
    $ numeraDRCs.sh 4
        
Podemos renombrarlos para mejor indicación:
    
    $ renombraDRCs.sh multipuntoV1
        
    $ ls drc*
    drc-4-L_lp_multipuntoV1.pcm
    drc-4-R_lp_multipuntoV1.pcm
    drc-5-L_mp_multipuntoV1.pcm
    drc-5-R_mp_multipuntoV1.pcm
    
Los subimos a la máquina FIRtro
    
    echo "put drc*" | sftp firtro@MyFIRtroIP
    
## 6. Actualizar FIRtro con el nuevo juego DRC

    ssh firtro@MyFIRtroIP
    cd
    mv drc* lspk/miAltavoz/44100/
    do_brutefir_config.py lspk/miAltavoz/44100/ | less
    
Veremos los coeff que cargan nuestro nuevos filtros pcm.
    
Si todo es correcto actualizamos brutefir_config y reiniciamos:
    
    do_brutefir_config.py lspk/miAltavoz/44100/ -w
    initfirtro.py &
    
Ahora tendremos los filtros disponibles para evaluarlos:

![](https://github.com/AudioHumLab/FIRtro/blob/master/doc/screenshots/drc_lista.png)

