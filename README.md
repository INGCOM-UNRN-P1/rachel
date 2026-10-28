# ⚡ RACHEL — Desensamblador y Visualizador de Jump Tables en C

> 📖 **Manual de Usuario:** Para una guía exhaustiva de comandos, banderas, arquitectura y ejemplos, consultá el [Manual de Uso](MANUAL.md).

RACHEL es una herramienta pedagógica diseñada para analizar sentencias `switch` y cadenas de `if-else` en C, desensamblando las tablas de salto (`Jump Tables`) generadas por el compilador y renderizando diagramas de flujo interactivos.

---

## 🎯 Alcance

### Qué cubre
- Desensamblado, inspección y análisis estático de estructuras de control de flujo bifurcado en C.
- Comparación técnica y pedagógica entre bifurcaciones `switch-case` y cadenas de `if-else`.
- Detección de generación de tablas de salto (Jump Tables) en código máquina compilado.
- Cálculo de densidad de etiquetas `case` y evaluación de costos asociados a la predicción de saltos (branch prediction).
- Emisión de diagramas de flujo de bifurcaciones en sintaxis Mermaid.
- `-O0` contra `-O2` por función (`rachel compare-opt`): instrucciones, saltos condicionales, llamadas y
  accesos a la pila de cada versión, y en español qué transformó el optimizador: inlining, variables en
  registros, vectorización (SIMD), desenrollado, saltos reemplazados por `cmov`, recursión de cola
  convertida en lazo y lazos resueltos en tiempo de compilación.
- Cadenas de `if` / `else if` de más de 4 comparaciones de una variable con constantes (`rachel cadenas`,
  también en `check` y su sección Markdown): con el assembly se distingue la que GCC ya convirtió en una
  tabla de la que quedó como una comparación tras otra, que conviene escribir como `switch` (tabla de
  saltos si los valores son densos; árbol de comparaciones si están dispersos).
- Saltos explicados en C (`rachel desazucarar`): el assembly con un comentario por cada `cmp`/`test` y
  salto condicional («salta a .L2 si x <= 5: es decir, cuando «x > 5» es falsa»), con la línea de C que
  lo origina y los nombres de las variables que da `gcc -fverbose-asm`.

### Qué no cubre (Límites y Delegación)
- Medición de contadores de hardware reales de branch misses (delegado a `ferro`).
- Extracción de mapas globales de llamadas (delegado a `giger`).
- Desazucarado sintáctico de código C a nivel de lenguaje (no contemplado).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Linux / POSIX o Windows (MSYS2 / WSL). Python >= 3.10.

### Dependencias Externas y Binarios
- `gcc` (para compilación y generación de código ensamblado `-S`).

### Integración en el Ecosistema
- CLI `rachel`.

---

## Uso Rápido

```bash
# 1. Analizar e inspeccionar switches en un archivo C
rachel switch parser.c

# 2. Emitir diagrama de flujo en sintaxis Mermaid
rachel switch parser.c --mermaid

# 3. Comparar costo temporal y de memoria entre switch e if-else
rachel compare parser.c

# 4. Generar reporte consolidado Markdown
rachel report parser.c

# 5. Salida estructurada JSON
rachel switch parser.c --json

# 6. Qué hizo el optimizador entre -O0 y -O2
rachel compare-opt parser.c

# 7. Cadenas de if-else que deberían ser un switch
rachel cadenas parser.c

# 8. El assembly con cada salto explicado en C
rachel desazucarar parser.c --funcion clasificar
```

<!-- p1:referencia:inicio — generado por p1-tools/scripts/readme_generado.py: no editar a mano -->

## Referencia rápida

### Requisitos

- Python ≥ 3.11 y [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Programas del sistema: `gcc`.

| Sistema | `gcc` |
|:--|:--|
| Debian / Ubuntu | `sudo apt install gcc` |
| Fedora | `sudo dnf install gcc` |
| Windows | incluido en el entorno de la cátedra (MSYS2 UCRT64) |
| macOS | `xcode-select --install` (clang como `gcc`) |

### Comandos

| Comando | Descripción |
|:--|:--|
| `rachel check`, `rachel switch` | Analiza las sentencias switch del código C, visualiza su diagrama de flujo y desensambla jump tables. |
| `rachel compare-opt` | Compara el assembly de -O0 y -O2 por función y explica en español qué transformó el optimizador. |
| `rachel cadenas` | Cadenas de if / else if de más de 4 comparaciones con constantes, que conviene escribir como switch. |
| `rachel desazucarar` | Assembly anotado: cada cmp/test y salto condicional con la condición en C que evalúa. |
| `rachel compare` | Compara el costo computacional entre la implementación de switch vs cadenas de if-else. |
| `rachel report` | Genera directamente la sección de reporte Markdown de RACHEL para Dredd. |
| `rachel doctor` | Verifica el estado del entorno de RACHEL (Python, GCC, objdump). |

Ayuda de cada comando: `rachel <comando> -h`.

### Salida JSON

Con `--json`, estos comandos emiten el resultado como JSON por la salida estándar, para usarlo desde scripts, ripley o dredd: `rachel check`, `rachel switch`, `rachel compare-opt`, `rachel cadenas`, `rachel doctor`. El de `doctor --json` lleva `schema_version` y `ok`.

### Códigos de salida

| Código | Significado |
|:--|:--|
| `0` | Terminó bien (en `doctor`: está todo lo requerido). |
| `1` | El comando encontró problemas (hallazgos, pruebas que fallan, un umbral que no se alcanza) o un dato no se pudo usar (un archivo ilegible, un formato inválido). |
| `2` | Error de uso: comando, opción o argumento inválido. |

<!-- p1:referencia:fin -->
