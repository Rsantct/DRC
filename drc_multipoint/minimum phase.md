Proporciona filtros minimum phase y linear phase, ambos con idéntica respuesta en magnitud.

Emmo, la variante `mp` puede resultar más adecuada en escenarios 'near field' con punto de escucha muy localizado. Los accidentes en la respuesta en frecuencia por debajo de la frecuencia de Shroeder en esa localización de escucha tendrán una naturaleza minimum phase invariable, entonces la corrección `mp` será óptima. Esta variante no introduce latencia.

La variante `lp` puede adaptarse mejor a escenarios 'mid field' tipo Hi-Fi doméstica con posiciones de escucha más variables. En este escenario es difícilmente precedecible una corrección en amplitud y su fase mínima asociada. Para calcular el filtro de drc, podremos confeccionar la respuesta `.frd` promediando varias medidas tomadas en un amplio espacio de posiciones de micrófono.
