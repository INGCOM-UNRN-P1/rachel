# ⚡ RACHEL — Desensamblador y Visualizador de Jump Tables en C

RACHEL es una herramienta pedagógica diseñada para analizar sentencias `switch` y cadenas de `if-else` en C, desensamblando las tablas de salto (`Jump Tables`) generadas por el compilador y renderizando diagramas de flujo interactivos.

---

## 🎯 Alcance

### Qué cubre
- Desensamblado, inspección y análisis estático de estructuras de control de flujo bifurcado en C.
- Comparación técnica y pedagógica entre bifurcaciones `switch-case` y cadenas de `if-else`.
- Detección de generación de tablas de salto (Jump Tables) en código máquina compilado.
- Cálculo de densidad de etiquetas `case` y evaluación de costos asociados a la predicción de saltos (branch prediction).
- Emisión de diagramas de flujo de bifurcaciones en sintaxis Mermaid.

### Qué no cubre (Límites y Delegación)
- Medición de contadores de hardware reales de branch misses (delegado a `ferro`).
- Extracción de mapas globales de llamadas (delegado a `giger`).
- Desazucarado sintáctico de código C a nivel de lenguaje (delegado a `morpheus`).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Linux / POSIX o Windows (MSYS2 / WSL). Python >= 3.10.

### Dependencias Externas y Binarios
- `gcc` o `clang`, `objdump`.

### Integración en el Ecosistema
- CLI `rachel`. Subcomando `rachel doctor`.

---

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
