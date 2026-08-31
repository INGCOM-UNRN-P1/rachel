---
title: "Manual de Referencia: rachel"
subtitle: "Rachel — Desensamblador y Verificador de Jump Tables O(1) en Sentencias Switch"
author: "Cátedra de Algoritmos y Programación"
date: "2026-08-31"
---

(manual-rachel)=
# Rachel — Desensamblador y Verificador de Jump Tables O(1) en Sentencias Switch

````{abstract}
**Rol en el ecosistema:** Desensamblado de código máquina y análisis de grafos de control para verificar si el compilador generó una tabla de saltos indexada O(1) (Jump Table / rodata) o una cascada ineficiente de comparaciones if-else O(N).
````

---

(manual-rachel-proposito)=
## 1. Propósito y Filosofía Pedagógica

La herramienta **`rachel`** forma parte del ecosistema oficial de software de la cátedra. Su diseño sigue principios pedagógicos rigurosos:

1. **Evidencia Técnica Directa**: Todo diagnóstico se fundamenta en la norma ISO C (C11/C23), en el modelo de memoria del sistema o en convenciones arquitectónicas formales.
2. **Acción Correctiva Concreta**: Cada advertencia incluye la prescripción técnica inmediata para resolver el defecto sin recurrir a conjeturas.
3. **Autonomía del Estudiante**: Facilita la autoevaluación local antes de la entrega final del trabajo práctico.
4. **Objetividad Docente**: Estandariza la corrección automática eliminando discrepancias subjetivas en la evaluación.

---

(manual-rachel-instalacion)=
## 2. Instalación y Diagnóstico del Entorno

````{important}
Asegurate de contar con el compilador GCC/Clang y las librerías del sistema instaladas antes de ejecutar `rachel`.
````

Para comprobar el estado de salud de tu entorno de trabajo y las dependencias auxiliares:

````{code-block} bash
# Comprobación de dependencias del sistema
rachel doctor
````

Si se detecta la falta de alguna utilidad (como `gdb`, `valgrind`, `clang-format` o `typst`), el comando indicará el paquete exacto a instalar según tu distribución GNU/Linux o entorno MSYS2.

---

(manual-rachel-comandos)=
## 3. Referencia Completa de Comandos CLI

A continuación se detallan los subcomandos principales disponibles en `rachel`:

| Sintaxis del Comando | Descripción y Efecto |
| :--- | :--- |
| `rachel check src/procesador.c` | Analiza las sentencias switch y reporta si usan Jump Tables O(1). |
| `rachel disasm src/main.c --function <fn>` | Muestra el código ensamblador coloreado de la estructura de salto. |
| `rachel optimize-switch src/despachador.c` | Sugiere densificación de etiquetas case para forzar Jump Table. |
| `rachel doctor` | Verifica la disponibilidad de objdump, GDB y compiladores. |

````{tip}
Podés agregar el flag `--json` a la mayoría de los comandos para exportar resultados en formato estructurado o `--md` para generar reportes Markdown para el informe de entrega.
````

---

(manual-rachel-tutorial)=
## 4. Tutorial Paso a Paso con Ejemplos Reales

### Caso de Estudio

Considerá el siguiente fragmento de código representativo:

````{code-block} c
:linenos:
#include <stdio.h>

// Switch denso analizado por Rachel: el compilador genera Jump Table O(1)
void despachar_comando(int cmd) {
    switch (cmd) {
        case 1: printf("Alta\n"); break;
        case 2: printf("Baja\n"); break;
        case 3: printf("Modificación\n"); break;
        case 4: printf("Listado\n"); break;
        default: printf("Invalido\n"); break;
    }
}
````

### Ejecución de la Herramienta

Ejecutá el análisis desde tu terminal:

````{code-block} bash
rachel check src/procesador.c
````

### Salida Obtenida en Consola

````{code-block} text
[✓] RACHEL SWITCH AUDIT: src/procesador.c en 'despachar_comando()':
    • Patrón detectado: Jump Table O(1) indexada en .rodata (4 entradas contiguas).
    • Instrucción de despacho: 'jmpq *0x402060(,%rdi,8)'
    • Complejidad temporal: O(1) constante (independiente de la cantidad de cases).
````

````{note}
Prestá atención a la explicación pedagógica generada: la herramienta no solo señala la línea del problema, sino que explica la causa raíz y el impacto en memoria o arquitectura.
````

---

(manual-rachel-ejercicios)=
## 5. Ejercicios Prácticos y Desafíos

Practicá el uso avanzado de **`rachel`** resolviendo los siguientes ejercicios:

````{exercise} Desafío 1: Verificación de Tabla de Saltos en Intérprete
Comprobar que el switch del despachador de opcodes compila a Jump Table.

**Instrucción de ejecución:**
```bash
rachel check src/interprete.c
```
````

````{solution} Desafío 1
```bash
rachel check src/interprete.c
# Verificá que la operación concluya exitosamente con código de salida 0.
```
````

````{exercise} Desafío 2: Densificación de Casos Esparsos
Transformar un switch disperso (case 1, case 1000, case 50000) en densidad contigua.

**Instrucción de ejecución:**
```bash
rachel optimize-switch src/comandos.c
```
````

````{solution} Desafío 2
```bash
rachel optimize-switch src/comandos.c
# Revisá el archivo generado o el informe en terminal para confirmar la resolución del problema.
```
````

````{exercise} Desafío 3: Inspección de Instrucciones Ensamblador
Desensamblar la función despachadora y examinar la tabla en `.rodata`.

**Instrucción de ejecución:**
```bash
rachel disasm src/procesador.c --function despachar_comando
```
````

````{solution} Desafío 3
```bash
rachel disasm src/procesador.c --function despachar_comando
# Comprobá que la salida confirme la ausencia de advertencias o errores pendientes.
```
````

---

(manual-rachel-makefile)=
## 6. Integración en el Flujo de Trabajo y Makefile

Para incorporar `rachel` de forma automática a tu flujo de desarrollo, agregá la siguiente regla en el `Makefile` de tu proyecto:

````{code-block} makefile
check-rachel:
	@echo "=== Ejecutando verificación con rachel ==="
	rachel check src/ include/

.PHONY: check-rachel
````

Ejecutá `make check-rachel` antes de cada commit para asegurar que tu código conserve el estado de aprobación.

---

(manual-rachel-arquitectura)=
## 7. Arquitectura Interna y Mecanismo Técnico

La herramienta **`rachel`** implementa un motor de alta precisión basado en:

- **Tecnología Núcleo:** `GNU objdump / GDB Disassembler + Jump Table .rodata Extractor + Control Flow Branch Predictor`.
- **Aislamiento y Determinismo:** Diseñada para operar sin efectos colaterales en entornos de integración continua (CI), terminales de estudiantes y servidores docentes headless.
- **Manejo de Errores Pedagógico:** Todo fallo de sintaxis, memoria o lógica se traduce en una acción prescriptiva concreta con su respectiva justificación técnica.

---

(manual-rachel-ecosistema)=
## 8. Integración y Conexión con el Ecosistema

````{note}
Ninguna herramienta opera de forma aislada. **`rachel`** forma parte del pipeline integral de evaluación, verificación y enseñanza de la cátedra.
````

### Diagrama de Flujo e Interoperabilidad

````{mermaid}
graph TD
    SRC[Código C: Sentencias switch] --> DAE[Daedalus: Compilador GCC]
    DAE -->|Binario Compilado| RCH[Rachel: Desensamblador O(1)]
    RCH -->|Inspección .rodata| OBJDUMP[GNU objdump Disassembler]
    RCH -->|Verificación O(1) vs O(N)| FRR[Ferro: Perfilador de Rendimiento]
````

### Matriz de Intercambio de Datos

| Canal | Herramientas Conectadas | Tipo de Datos Transferidos |
| :--- | :--- | :--- |
| **Entradas (Inputs)** | - `Binarios compilados con sentencias switch` | Código fuente, AST, binarios, testcases, contratos |
| **Salidas (Outputs)** | - `ferro (análisis de saltos)`
- `deckard (ejercicios de bajo nivel)` | Informes Markdown, diagnósticos Rich, JSON, actas |
| **Sincronización** | `daedalus`, `ferro`, `bishop` | Validación cruzada, flags compartidos y autofix |

### Pipeline de Integración Recomendado

Podés encadenar `rachel` con otras herramientas del ecosistema en una única línea de comando:

````{code-block} bash
# Pipeline de integración típico
rachel check src/despachador.c --disasm
````

