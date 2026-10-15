# Visor de paradas y rutas

`mapa_revision.html` es un **visor** para ver las paradas y rutas sobre un mapa. Revisar a mano es opcional: la
entrega de datos es `../export/paraderos.csv` (con sus atributos `precision`, `evidencia` y `confianza`).

## Uso
1. Abrir `mapa_revision.html` en el navegador (necesita internet para los mosaicos del mapa).
2. Elegir **sistema** y **servicio**; tocar una parada de la lista para centrarla.
3. **Colorear por** (arriba):
   - *precisión (Google)*: verde = exacta, ámbar = aproximada con parada de Google cerca, rojo = aproximada
     sin parada en Google, gris azulado = oficial.
   - *confianza del método*: alta / media / baja.
4. Círculo = sentido 1, cuadrado = sentido 2. La ficha muestra el nombre del sentido y el origen de la coordenada.
5. Rombo morado **G** = lo que dice Google; cuadrado **I** = interpolación por imagen (±170 m).

## Corrección opcional (solo alimentadores)
Las herramientas de corrección están ocultas por defecto. Para activarlas abre el visor con `?editar=1` al
final de la ruta (por ejemplo `mapa_revision.html?editar=1`). Incluyen el filtro «solo pendientes», el modo
auditoría y la exportación/importación de correcciones.

Botones ✔ correcta · 📍 mover · ✖ no existe, o pegar un enlace de Google Maps en el comentario (se extrae la
coordenada del enlace completo de la barra de direcciones, no del enlace corto). **▶ Modo auditoría** recorre
una cola de paradas. Exporta el CSV al terminar (el navegador guarda las decisiones solo en ese equipo).

Para aplicarlas: copiar el CSV a `../data/fuentes/correcciones_paradas.csv` y correr
`geocodificar_alimentadores.py`, `pipeline.run paraderos` y `pipeline.run export`. Una parada corregida queda con
`confianza = verificada` y `precision = exacta` (`evidencia = revision_humana`).

## Regenerar el visor
```bash
.venv/bin/python deliveries/week10/code/scripts/03_georef/generar_revision.py          # solo el HTML
.venv/bin/python deliveries/week10/code/scripts/03_georef/generar_revision.py --csv    # + revision_paradas.csv
```
