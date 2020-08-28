### Discusión: filtros de fase lineal para DRC

A modo experimental, `roomEQ.py` proporciona filtros minimum phase y linear phase, ambos con idéntica respuesta en magnitud.

Emmo, la variante resulta más adecuada en escenarios con punto de escucha localizado. Los accidentes en la respuesta en frecuencia por debajo de la frecuencia de Shroeder en esa localización de escucha tendrán una naturaleza minimum phase invariable, entonces la corrección minimum-phase será óptima. Esta variante no introduce latencia.

La variante linear-phase puede adaptarse mejor a escenarios de uso doméstico con posiciones de escucha variables. En este escenario es difícilmente precedecible una corrección en amplitud y su fase mínima asociada. Para calcular el filtro de drc, podremos confeccionar la respuesta `.frd` promediando varias medidas tomadas en un amplio espacio de posiciones de micrófono en la sala.

