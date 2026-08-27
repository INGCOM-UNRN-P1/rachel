"""Motor de desensamblado y análisis de estructuras de control en RACHEL."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from rachel.core.models import CasoSwitch, EstructuraControl, ReporteEstructuras


def extraer_switches_c(contenido: str, ruta_archivo: Path) -> List[EstructuraControl]:
    """Extrae bloques switch definidos en el código C."""
    patron_switch = re.compile(r"^\s*switch\s*\(([^)]+)\)\s*\{", re.MULTILINE)
    estructuras = []

    for m in patron_switch.finditer(contenido):
        start_pos = m.end() - 1
        line_start = contenido[:m.start()].count("\n") + 1

        # Balancear llaves del bloque switch
        brace_count = 0
        end_pos = start_pos
        for i in range(start_pos, len(contenido)):
            if contenido[i] == '{':
                brace_count += 1
            elif contenido[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break

        cuerpo = contenido[m.start():end_pos + 1]
        line_end = contenido[:end_pos].count("\n") + 1

        # Extraer casos
        casos = []
        re_case = re.compile(r"\b(case\s+([^:]+)|default)\s*:", re.MULTILINE)
        valores_numericos = []

        for cm in re_case.finditer(cuerpo):
            etiqueta = cm.group(2).strip() if cm.group(2) else "default"
            linea_caso = line_start + cuerpo[:cm.start()].count("\n")
            es_def = (cm.group(1) == "default")

            casos.append(CasoSwitch(
                etiqueta=etiqueta,
                linea=linea_caso,
                es_default=es_def,
            ))

            # Intentar parsear número
            try:
                val_num = int(etiqueta, 0)
                valores_numericos.append(val_num)
            except Exception:
                pass

        # Calcular densidad de casos
        densidad = 1.0
        if len(valores_numericos) >= 2:
            rango = max(valores_numericos) - min(valores_numericos) + 1
            densidad = len(valores_numericos) / rango if rango > 0 else 1.0

        # Heurística preliminar
        if len(casos) >= 4 and densidad >= 0.5:
            estrategia = "jump_table"
            explicacion = (
                f"El switch posee {len(casos)} casos con alta densidad ({densidad:.2f}). "
                "GCC genera típicamente una Tabla de Saltos (Jump Table) en .rodata con costo O(1)."
            )
        elif len(casos) >= 5:
            estrategia = "binary_tree_cmp"
            explicacion = (
                f"El switch posee casos dispersos (densidad {densidad:.2f}). "
                "GCC genera un Árbol Binario de Comparaciones sucesivas con costo O(log N)."
            )
        else:
            estrategia = "sequential_cmp"
            explicacion = (
                f"El switch posee pocos casos ({len(casos)}). "
                "GCC genera comparaciones secuenciales directas con costo O(N)."
            )

        # Generar diagrama Mermaid
        diagrama = _generar_mermaid_switch(casos, m.group(1).strip())

        estructuras.append(EstructuraControl(
            tipo="switch",
            funcion=_buscar_nombre_funcion_envolvente(contenido, m.start()),
            linea_inicio=line_start,
            linea_fin=line_end,
            codigo_fuente=cuerpo,
            casos=casos,
            estrategia_compilacion=estrategia,
            densidad_casos=densidad,
            diagrama_mermaid=diagrama,
            explicacion_pedagogica=explicacion,
        ))

    return estructuras


def _buscar_nombre_funcion_envolvente(contenido: str, pos: int) -> str:
    """Busca el nombre de la función que contiene la posición pos."""
    texto_previo = contenido[:pos]
    re_fn = re.compile(r"^\s*(?:[a-zA-Z0-9_*]+\s+)+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{", re.MULTILINE)
    matches = list(re_fn.finditer(texto_previo))
    if matches:
        return matches[-1].group(1)
    return "main"


def _generar_mermaid_switch(casos: List[CasoSwitch], condicion: str) -> str:
    """Genera diagrama de flujo Mermaid para el switch."""
    lineas = ["graph TD", f'    start["switch ({condicion})"]']
    for idx, c in enumerate(casos, 1):
        lbl = f"case {c.etiqueta}" if not c.es_default else "default"
        lineas.append(f'    start -->|{lbl}| node_{idx}["Acción ({lbl})"]')
    return "\n".join(lineas)


def analizar_assembly_real(
    archivo_c: Path,
    opt_level: str = "-O2",
) -> List[str]:
    """Compila con GCC -S y extrae las instrucciones assembly relevantes para el switch."""
    gcc = shutil.which("gcc") or "gcc"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_s = Path(tmp_dir) / "out.s"
        cmd = [gcc, "-S", opt_level, "-std=c11", str(archivo_c.resolve()), "-o", str(tmp_s)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and tmp_s.is_file():
            lineas = tmp_s.read_text(encoding="utf-8").splitlines()
            # Filtrar directivas de depuración pesadas
            return [l.strip() for l in lineas if l.strip() and not l.strip().startswith((".cfi_", ".file", ".ident"))]
    return []


def analizar_archivo_c(
    archivo: Path,
    opt_level: str = "-O2",
) -> ReporteEstructuras:
    """Analiza todas las estructuras de control y desensambla el archivo C."""
    archivo = Path(archivo)
    if not archivo.is_file():
        raise FileNotFoundError(f"No se encontró el archivo: {archivo}")

    contenido = archivo.read_text(encoding="utf-8")
    switches = extraer_switches_c(contenido, archivo)

    # Si hay switches, intentar refinar con el assembly real
    if switches:
        asm_lines = analizar_assembly_real(archivo, opt_level=opt_level)
        if asm_lines:
            tiene_jump_table = any("jmp\t*" in l or "jmp *" in l or ".quad\t.L" in l or ".long\t.L" in l for l in asm_lines)
            for s in switches:
                s.instrucciones_assembly = [l for l in asm_lines if not l.startswith(".LFB")][:25]
                if tiene_jump_table:
                    s.estrategia_compilacion = "jump_table"
                    s.explicacion_pedagogica = (
                        f"Verificado por GCC ({opt_level}): Se generó una Tabla de Saltos (Jump Table) en memoria .rodata. "
                        "El salto se realiza en tiempo constante O(1) indexando un puntero indirecto."
                    )

    return ReporteEstructuras(
        archivo=archivo,
        estructuras=switches,
    )
