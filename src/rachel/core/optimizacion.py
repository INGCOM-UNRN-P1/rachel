"""-O0 contra -O2, cadenas de if-else que piden un switch y saltos explicados en C (Ola 19).

- `comparar_optimizacion`: compila el archivo con -O0 y con -O2 y, por función, cuenta instrucciones,
  saltos condicionales, llamadas y accesos a la pila, y explica qué transformó el optimizador
  (inlining, variables en registros, vectorización, desenrollado, saltos reemplazados por `cmov`,
  recursión de cola convertida en lazo, lazos resueltos en tiempo de compilación).
- `cadenas_if`: las cadenas `if (x == A) … else if (x == B) …` sobre la misma variable con más de 4
  comparaciones; con el assembly de -O2 se distingue la que GCC ya convirtió en tabla de saltos de la
  que quedó como N comparaciones seguidas, que es la que conviene escribir como `switch`.
- `desazucarar`: el assembly anotado: cada `cmp`/`test` + salto condicional con la condición en C que
  evalúa («salta a .L2 si x <= 5»), contrastada con la del fuente (la línea de C que anota GCC con
  `-fverbose-asm`, que también da el nombre de la variable de cada operando).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rachel.core.analyzer import validar_opt_level


class SinCompilador(RuntimeError):
    pass


def compilar_asm(archivo: Path, opt: str, verbose: bool = False) -> str:
    """El assembly AT&T de x86-64 del archivo (gcc -S), sin la información de unwinding."""
    validar_opt_level(opt)
    gcc = shutil.which("gcc")
    if not gcc:
        raise SinCompilador("hace falta gcc para compilar a assembly.")
    with tempfile.TemporaryDirectory(prefix="rachel-") as tmp:
        salida = Path(tmp) / "out.s"
        cmd = [gcc, "-S", opt, "-std=c11", "-fno-asynchronous-unwind-tables", "-fno-ident",
               *(["-fverbose-asm"] if verbose else []), str(Path(archivo).resolve()), "-o", str(salida)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            raise SinCompilador(f"{Path(archivo).name} no compila:\n{res.stderr.strip()[:800]}")
        return salida.read_text(encoding="utf-8", errors="replace")


def funciones_asm(asm: str) -> Dict[str, List[str]]:
    """Nombre → líneas (sin la etiqueta) de cada función del assembly (`.type f, @function`)."""
    nombres = re.findall(r"^\s*\.type\s+([\w.$]+),\s*@function", asm, re.M)
    lineas = asm.splitlines()
    resultado: Dict[str, List[str]] = {}
    for nombre in nombres:
        try:
            inicio = lineas.index(f"{nombre}:")
        except ValueError:
            continue
        cuerpo: List[str] = []
        for linea in lineas[inicio + 1:]:
            if re.match(rf"^\s*\.size\s+{re.escape(nombre)},", linea):
                break
            cuerpo.append(linea)
        resultado[nombre] = cuerpo
    return resultado


def instrucciones(cuerpo: List[str]) -> List[Tuple[str, str]]:
    """(mnemónico, operandos) de cada instrucción, sin etiquetas, directivas ni comentarios."""
    resultado = []
    for linea in cuerpo:
        texto = linea.split("#", 1)[0].strip()
        if not texto or texto.endswith(":") or texto.startswith("."):
            continue
        partes = texto.split(None, 1)
        resultado.append((partes[0], partes[1].strip() if len(partes) > 1 else ""))
    return resultado


_SIMD = re.compile(r"^v?(p(add|sub|mul|madd|max|min|and|or|cmp|sll|srl|sra|avg|abs)\w*|(add|sub|mul|div|max|min)p[sd])$")


@dataclass
class Metricas:
    instrucciones: int = 0
    saltos_condicionales: int = 0
    llamadas: List[str] = field(default_factory=list)
    accesos_pila: int = 0
    simd: int = 0
    cmov: int = 0
    saltos_atras: int = 0


def metricas(cuerpo: List[str]) -> Metricas:
    m = Metricas()
    etiquetas_vistas = set()
    for linea in cuerpo:
        texto = linea.split("#", 1)[0].strip()
        if texto.endswith(":"):
            etiquetas_vistas.add(texto[:-1])
            continue
        if not texto or texto.startswith("."):
            continue
        partes = texto.split(None, 1)
        mnem, ops = partes[0], (partes[1].strip() if len(partes) > 1 else "")
        m.instrucciones += 1
        if mnem.startswith("j") and mnem != "jmp":
            m.saltos_condicionales += 1
        if mnem.startswith("j") and ops in etiquetas_vistas:
            m.saltos_atras += 1
        if mnem.startswith("call"):
            m.llamadas.append(ops.split("@")[0])
        if "(%rbp)" in ops or "(%rsp)" in ops:
            m.accesos_pila += 1
        if _SIMD.match(mnem):
            m.simd += 1
        if mnem.startswith(("cmov", "set")):
            m.cmov += 1
    return m


def _desenrollado(cuerpo: List[str]) -> bool:
    """Un lazo cuyo cuerpo es la misma secuencia de mnemónicos repetida (el compilador lo desenrolló)."""
    lineas = [ln.split("#", 1)[0].strip() for ln in cuerpo]
    for i, linea in enumerate(lineas):
        if not linea.endswith(":"):
            continue
        etiqueta = linea[:-1]
        for j in range(i + 1, len(lineas)):
            partes = lineas[j].split()
            if len(partes) == 2 and partes[0].startswith("j") and partes[1] == etiqueta:
                mnems = [ln.split()[0] for ln in lineas[i + 1:j] if ln and not ln.endswith(":") and not ln.startswith(".")]
                for periodo in range(2, len(mnems) // 2 + 1):
                    if len(mnems) >= 2 * periodo and mnems[:periodo] == mnems[periodo:2 * periodo]:
                        return True
                break
    return False


@dataclass
class ComparacionFuncion:
    nombre: str
    o0: Metricas
    o2: Optional[Metricas]  # None: la función no está en -O2 (se incorporó en sus llamadores)
    transformaciones: List[str] = field(default_factory=list)


def comparar_optimizacion(archivo: Path, opt: str = "-O2") -> List[ComparacionFuncion]:
    bajo = funciones_asm(compilar_asm(archivo, "-O0"))
    alto_asm = compilar_asm(archivo, opt)
    alto = funciones_asm(alto_asm)
    propias = set(bajo)
    resultado: List[ComparacionFuncion] = []
    for nombre, cuerpo in bajo.items():
        m0 = metricas(cuerpo)
        if nombre not in alto:
            resultado.append(ComparacionFuncion(nombre, m0, None, [
                f"Inlining: {nombre}() no existe en {opt}: el compilador copió su código dentro de cada función "
                "que la llamaba, sin el costo de la llamada (sólo pasa con las funciones static)."]))
            continue
        m2 = metricas(alto[nombre])
        t: List[str] = []
        incorporadas = sorted({f for f in m0.llamadas if f in propias and f != nombre} - set(m2.llamadas))
        if incorporadas:
            t.append(f"Inlining: las llamadas a {', '.join(f'{f}()' for f in incorporadas)} desaparecieron: su código "
                     "quedó dentro de esta función, sin el costo de llamar y volver.")
        if nombre in m0.llamadas and nombre not in m2.llamadas and m2.saltos_atras:
            t.append("Recursión de cola convertida en lazo: la llamada recursiva pasó a ser un salto hacia atrás, "
                     "sin apilar un marco por llamada.")
        if m0.accesos_pila and m2.accesos_pila < m0.accesos_pila / 2:
            t.append(f"Variables en registros: con -O0 cada variable vive en la pila y se lee y escribe en memoria "
                     f"({m0.accesos_pila} accesos); con {opt}, {m2.accesos_pila}: quedan en los registros del procesador.")
        if m2.simd > m0.simd:
            t.append(f"Vectorización: {m2.simd} instrucciones SIMD (registros %xmm/%ymm) procesan varios elementos "
                     "a la vez; el lazo avanza de a 4 u 8 en lugar de a 1.")
        if _desenrollado(alto[nombre]):
            t.append("Desenrollado: el cuerpo del lazo está repetido dentro de cada vuelta, para comparar y saltar "
                     "menos veces.")
        if m2.cmov > m0.cmov and m2.saltos_condicionales < m0.saltos_condicionales:
            t.append(f"Saltos reemplazados por selección: {m2.cmov} instrucciones cmov/set eligen el resultado sin "
                     "saltar, y el procesador no tiene que adivinar hacia dónde va un if.")
        if m0.saltos_atras and not m2.saltos_atras and not m2.llamadas and not m2.saltos_condicionales:
            t.append("Lazo resuelto en tiempo de compilación: en -O0 hay un lazo y en "
                     f"{opt} ninguno, ni saltos ni llamadas: el compilador calculó el resultado o lo reemplazó por una "
                     "fórmula.")
        if not t and m2.instrucciones < m0.instrucciones:
            t.append("Simplificación general: menos instrucciones para lo mismo (constantes calculadas de antemano, "
                     "operaciones redundantes eliminadas).")
        resultado.append(ComparacionFuncion(nombre, m0, m2, t))
    return resultado


# ── Cadenas de if-else sobre constantes ─────────────────────────────────────────────────────────

MIN_COMPARACIONES = 5  # «más de 4 comparaciones»
_IF_IGUAL = re.compile(r"\bif\s*\(\s*(?:(?P<var>[A-Za-z_]\w*)\s*==\s*(?P<cte>[-+]?\w+|'[^']*')"
                       r"|(?P<cte2>[-+]?\w+|'[^']*')\s*==\s*(?P<var2>[A-Za-z_]\w*))\s*\)")


@dataclass
class CadenaIf:
    funcion: str
    variable: str
    linea_inicio: int
    linea_fin: int
    comparaciones: int
    constantes: List[str] = field(default_factory=list)
    convertida_por_gcc: Optional[bool] = None  # None: no se pudo mirar el assembly
    saltos_condicionales: Optional[int] = None
    mensaje: str = ""


def _es_constante(texto: str) -> bool:
    return bool(re.fullmatch(r"[-+]?(0[xX][0-9a-fA-F]+|\d+)[uUlL]*|'[^']*'|[A-Z_][A-Z0-9_]*", texto))


def cadenas_if(contenido: str, enmascarado: str) -> List[CadenaIf]:
    """Las cadenas if / else if que comparan la misma variable con constantes."""
    from rachel.core.analyzer import _buscar_nombre_funcion_envolvente

    cadenas: List[CadenaIf] = []
    actual: Optional[CadenaIf] = None
    fin_anterior = 0
    for m in _IF_IGUAL.finditer(enmascarado):
        var = m.group("var") or m.group("var2")
        cte = m.group("cte") or m.group("cte2")
        linea = enmascarado[:m.start()].count("\n") + 1
        if var is None or cte is None or not _es_constante(cte) or var == cte:
            actual = None
            continue
        sigue = (actual is not None and actual.variable == var
                 and re.search(r"\belse\s*$", enmascarado[fin_anterior:m.start()]) is not None)
        if sigue and actual is not None:
            actual.comparaciones += 1
            actual.linea_fin = linea
            actual.constantes.append(cte)
        else:
            actual = CadenaIf(_buscar_nombre_funcion_envolvente(enmascarado, m.start()), var, linea, linea, 1, [cte])
            cadenas.append(actual)
        fin_anterior = m.end()
        # El cuerpo del if: hasta el `else` que continúa la cadena (o el final).
        nivel, i = 0, m.end()
        while i < len(enmascarado):
            c = enmascarado[i]
            if c == "{":
                nivel += 1
            elif c == "}":
                nivel -= 1
                if nivel == 0:
                    fin_anterior = i + 1
                    break
            elif c == ";" and nivel == 0:
                fin_anterior = i + 1
                break
            i += 1
    return [c for c in cadenas if c.comparaciones >= MIN_COMPARACIONES]


def evaluar_cadenas(archivo: Path, opt: str = "-O2") -> List[CadenaIf]:
    from rachel.core.masking import enmascarar_no_codigo

    contenido = Path(archivo).read_text(encoding="utf-8", errors="replace")
    cadenas = cadenas_if(contenido, enmascarar_no_codigo(contenido))
    if not cadenas:
        return cadenas
    try:
        funciones = funciones_asm(compilar_asm(archivo, opt))
    except SinCompilador:
        funciones = {}
    for c in cadenas:
        cuerpo = funciones.get(c.funcion)
        if cuerpo is not None:
            c.saltos_condicionales = metricas(cuerpo).saltos_condicionales
            # Una tabla de saltos (jmp *) o de valores (CSWTCH: el resultado de cada caso en un arreglo), o
            # tan pocos saltos que ya no es una comparación por constante.
            c.convertida_por_gcc = (any(re.search(r"\bjmp\s+\*|CSWTCH", ln) for ln in cuerpo)
                                    or c.saltos_condicionales <= 2)
        if c.convertida_por_gcc:
            c.mensaje = (f"La cadena de {c.comparaciones} if-else sobre '{c.variable}' (líneas {c.linea_inicio}–"
                         f"{c.linea_fin}) la convirtió GCC ({opt}) en una tabla (de saltos o de resultados): un switch lo dice "
                         "explícitamente y no depende de que el optimizador lo descubra.")
        else:
            saltos = f" ({c.saltos_condicionales} saltos condicionales en la función)" if c.saltos_condicionales else ""
            valores = [int(x, 0) for x in c.constantes if re.fullmatch(r"[-+]?(0[xX][0-9a-fA-F]+|\d+)", x)]
            densos = len(valores) == len(c.constantes) and max(valores) - min(valores) + 1 <= 2 * len(valores)
            ventaja = ("GCC puede usar una tabla de saltos y llegar al caso en un solo salto" if densos else
                       "los valores están dispersos, así que GCC no usaría una tabla, pero sí un árbol de comparaciones "
                       f"(unas {max(1, len(c.constantes).bit_length())} en lugar de {c.comparaciones})")
            c.mensaje = (f"La cadena de {c.comparaciones} if-else compara '{c.variable}' con constantes una tras otra "
                         f"(líneas {c.linea_inicio}–{c.linea_fin}): en el peor caso hace {c.comparaciones} "
                         f"comparaciones{saltos}. Con un switch, {ventaja}.")
    return cadenas


# ── Desazucarado de los saltos condicionales ────────────────────────────────────────────────────

_SALTOS = {
    "je": ("==", ""), "jz": ("==", ""), "jne": ("!=", ""), "jnz": ("!=", ""),
    "jl": ("<", ""), "jnge": ("<", ""), "jle": ("<=", ""), "jng": ("<=", ""),
    "jg": (">", ""), "jnle": (">", ""), "jge": (">=", ""), "jnl": (">=", ""),
    "jb": ("<", " (sin signo)"), "jnae": ("<", " (sin signo)"), "jc": ("<", " (sin signo)"),
    "jbe": ("<=", " (sin signo)"), "jna": ("<=", " (sin signo)"), "ja": (">", " (sin signo)"),
    "jnbe": (">", " (sin signo)"), "jae": (">=", " (sin signo)"), "jnb": (">=", " (sin signo)"),
    "jnc": (">=", " (sin signo)"), "js": ("< 0", ""), "jns": (">= 0", ""),
}
_NEGACION = {"==": "!=", "!=": "==", "<": ">=", ">=": "<", ">": "<=", "<=": ">"}


def _operandos(texto: str) -> List[str]:
    """Los operandos AT&T separados por comas fuera de paréntesis."""
    partes, nivel, actual = [], 0, ""
    for c in texto:
        if c == "(":
            nivel += 1
        elif c == ")":
            nivel -= 1
        if c == "," and nivel == 0:
            partes.append(actual.strip())
            actual = ""
        else:
            actual += c
    if actual.strip():
        partes.append(actual.strip())
    return partes


def _nombre(operando: str, nombre_gcc: str) -> str:
    if nombre_gcc and not re.fullmatch(r"_\d+|tmp\d+|D\.\d+", nombre_gcc):
        return re.sub(r"_\d+$", "", nombre_gcc)
    if operando.startswith("$"):
        return operando[1:]
    return operando


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"(\d)[uUlL]+\b", r"\1", texto))


def _equivalentes(izq: str, rel: str, der: str) -> List[str]:
    """`x <= 2` también se escribe `x < 3` (y al revés): GCC suele cambiar la constante."""
    formas = [f"{izq} {rel} {der}"]
    try:
        n = int(der, 0)
    except ValueError:
        return formas
    otra = {"<=": ("<", n + 1), "<": ("<=", n - 1), ">": (">=", n + 1), ">=": (">", n - 1)}.get(rel)
    if otra:
        formas.append(f"{izq} {otra[0]} {otra[1]}")
    return formas


def desazucarar(archivo: Path, opt: str = "-O0", funcion: Optional[str] = None) -> str:
    """El assembly de cada función con un comentario en español por cada salto condicional."""
    asm = compilar_asm(archivo, opt, verbose=True)
    salida: List[str] = []
    for nombre, cuerpo in funciones_asm(asm).items():
        if funcion and nombre != funcion:
            continue
        salida.append(f"{nombre}:")
        fuente_actual = ""
        ultima_comparacion: Optional[Tuple[str, str, str]] = None  # (mnemónico, izquierda, derecha)
        for linea in cuerpo:
            limpia = linea.strip()
            m_fuente = re.match(r"^#\s*(?:.*/)?[^/:]+\.c:(\d+):\s?(.*)$", limpia)
            if m_fuente:
                if m_fuente.group(2).strip() != fuente_actual:
                    fuente_actual = m_fuente.group(2).strip()
                    salida.append(f"    # ── línea {m_fuente.group(1)}: {fuente_actual}")
                continue
            if not limpia or (limpia.startswith(".") and not limpia.endswith(":")) or limpia.startswith("#"):
                continue
            instr, _, comentario = limpia.partition("#")
            instr = instr.strip()
            if instr.endswith(":"):
                salida.append(instr)
                continue
            partes = instr.split(None, 1)
            mnem, ops = partes[0], (partes[1].strip() if len(partes) > 1 else "")
            instr = f"{mnem} {ops}".strip()
            nota = ""
            if mnem.startswith(("cmp", "test")):
                operandos = _operandos(ops)
                nombres = [n.strip() for n in comentario.split(",")] if comentario.strip() else []
                nombres += [""] * (len(operandos) - len(nombres))
                if len(operandos) == 2:
                    fuente_op, destino = (_nombre(o, n) for o, n in zip(operandos, nombres, strict=False))
                    ultima_comparacion = (mnem, destino, fuente_op)
                    if mnem.startswith("cmp"):
                        nota = f"compara {destino} con {fuente_op}"
                    elif fuente_op == destino:
                        nota = f"mira si {destino} es 0 (o negativo)"
                    else:
                        nota = f"calcula {destino} & {fuente_op} sólo para ver el resultado"
            elif mnem in _SALTOS and ultima_comparacion is not None:
                rel, signo = _SALTOS[mnem]
                tipo, izq, der = ultima_comparacion
                if tipo.startswith("test"):
                    expr = f"{izq} {rel if rel in ('==', '!=') else rel} 0" if izq == der else f"({izq} & {der}) {rel} 0"
                    if rel in ("< 0", ">= 0"):
                        expr = f"{izq} {rel}"
                else:
                    expr = f"{izq} {rel} {der}" if rel not in ("< 0", ">= 0") else f"{izq} - {der} {rel}"
                nota = f"salta a {ops} si {expr}{signo}"
                negadas = _equivalentes(izq, _NEGACION[rel], der) if rel in _NEGACION and tipo.startswith("cmp") else []
                directas = _equivalentes(izq, rel, der) if tipo.startswith("cmp") and rel in _NEGACION else [expr]
                fuente_norm = _normalizar(fuente_actual)
                negada = next((n for n in negadas if _normalizar(n) in fuente_norm), None)
                directa = next((d for d in directas if _normalizar(d) in fuente_norm), None)
                if negada:
                    nota += f": es decir, cuando «{negada}» es falsa (el salto saltea el bloque del if)"
                elif directa:
                    nota += f": es decir, cuando «{directa}» es verdadera"
            elif mnem == "jmp":
                nota = f"salta siempre a {ops}"
            salida.append((f"    {instr:<34}" + (f"  # {nota}" if nota else "")).rstrip())
        salida.append("")
    return "\n".join(salida).rstrip() + "\n"
