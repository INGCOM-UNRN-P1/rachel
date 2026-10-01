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
| `rachel compare` | Compara el costo computacional entre la implementación de switch vs cadenas de if-else. |
| `rachel report` | Genera directamente la sección de reporte Markdown de RACHEL para Dredd. |
| `rachel doctor` | Verifica el estado del entorno de RACHEL (Python, GCC, objdump). |

Ayuda de cada comando: `rachel <comando> -h`.

### Salida JSON

Con `--json`, estos comandos emiten el resultado como JSON por la salida estándar, para usarlo desde scripts, ripley o dredd: `rachel check`, `rachel switch`, `rachel doctor`. El de `doctor --json` lleva `schema_version` y `ok`.

### Códigos de salida

| Código | Significado |
|:--|:--|
| `0` | Terminó bien (en `doctor`: está todo lo requerido). |
| `1` | El comando encontró problemas (hallazgos, pruebas que fallan, un umbral que no se alcanza) o un dato no se pudo usar (un archivo ilegible, un formato inválido). |
| `2` | Error de uso: comando, opción o argumento inválido. |

<!-- p1:referencia:fin -->
