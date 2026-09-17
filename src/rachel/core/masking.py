"""Enmascarado de regiones que no son código ejecutable.

El motor de RACHEL busca `switch` con expresiones regulares sobre el fuente. Sin
enmascarar, un `switch` escrito dentro de un comentario, de una cadena o de un
bloque `#if 0` se analiza como si fuera código real (y encima dispara una
compilación con GCC para "refinarlo").

Todas las funciones reemplazan el contenido por espacios en vez de borrarlo,
de modo que los offsets y los números de línea del original se mantienen.
"""

from __future__ import annotations

import re

_INICIO_IF_FALSO = re.compile(r"^\s*#\s*if\s+0\s*(?://.*|/\*.*)?$")
_INICIO_CONDICIONAL = re.compile(r"^\s*#\s*(if|ifdef|ifndef)\b")
_FIN_CONDICIONAL = re.compile(r"^\s*#\s*endif\b")
_RAMA_ALTERNATIVA = re.compile(r"^\s*#\s*(else|elif)\b")


def _blanquear(texto: str) -> str:
    """Sustituye cada carácter por un espacio, conservando los saltos de línea."""
    return "".join("\n" if c == "\n" else " " for c in texto)


def enmascarar_comentarios_y_literales(contenido: str) -> str:
    """Blanquea comentarios de línea, de bloque y literales de cadena/carácter."""
    resultado = []
    i = 0
    n = len(contenido)

    while i < n:
        c = contenido[i]
        par = contenido[i:i + 2]

        if par == "//":
            fin = contenido.find("\n", i)
            fin = n if fin == -1 else fin
            resultado.append(_blanquear(contenido[i:fin]))
            i = fin
        elif par == "/*":
            fin = contenido.find("*/", i + 2)
            fin = n if fin == -1 else fin + 2
            resultado.append(_blanquear(contenido[i:fin]))
            i = fin
        elif c in ('"', "'"):
            comilla = c
            j = i + 1
            while j < n:
                if contenido[j] == "\\":
                    j += 2
                    continue
                if contenido[j] == comilla:
                    j += 1
                    break
                if contenido[j] == "\n":
                    break
                j += 1
            resultado.append(_blanquear(contenido[i:j]))
            i = j
        else:
            resultado.append(c)
            i += 1

    return "".join(resultado)


def enmascarar_bloques_inactivos(contenido: str) -> str:
    """Blanquea el cuerpo de los bloques `#if 0` (incluidos los anidados)."""
    lineas = contenido.splitlines(keepends=True)
    salida = []
    # Profundidad de condicionales dentro del bloque `#if 0` que se está
    # descartando; None cuando no estamos dentro de ninguno.
    profundidad: int | None = None

    for linea in lineas:
        if profundidad is None:
            if _INICIO_IF_FALSO.match(linea.rstrip("\n")):
                profundidad = 1
                salida.append(linea)  # la directiva en sí se conserva
            else:
                salida.append(linea)
            continue

        if _INICIO_CONDICIONAL.match(linea):
            profundidad += 1
            salida.append(_blanquear(linea))
        elif _FIN_CONDICIONAL.match(linea):
            profundidad -= 1
            if profundidad == 0:
                profundidad = None
                salida.append(linea)
            else:
                salida.append(_blanquear(linea))
        elif profundidad == 1 and _RAMA_ALTERNATIVA.match(linea):
            # `#else`/`#elif` del `#if 0`: a partir de acá el código sí compila.
            profundidad = None
            salida.append(linea)
        else:
            salida.append(_blanquear(linea))

    return "".join(salida)


def enmascarar_no_codigo(contenido: str) -> str:
    """Aplica todo el enmascarado previo al análisis por expresiones regulares."""
    return enmascarar_bloques_inactivos(enmascarar_comentarios_y_literales(contenido))
