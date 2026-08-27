# ⚡ RACHEL — Desensamblador y Visualizador de Jump Tables en C

RACHEL es una herramienta pedagógica diseñada para analizar sentencias `switch` y cadenas de `if-else` en C, desensamblando las tablas de salto (`Jump Tables`) generadas por el compilador y renderizando diagramas de flujo interactivos.

## Uso Rápido

```bash
# 1. Analizar e inspeccionar switches en un archivo C
rachel switch parser.c

# 2. Emitir diagrama de flujo en sintaxis Mermaid
rachel switch parser.c --mermaid

# 3. Comparar costo temporal y de memoria entre switch e if-else
rachel compare parser.c

# 4. Salida estructurada JSON
rachel switch parser.c --json
```
