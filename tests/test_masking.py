"""Regresión de RACHEL-D0301/D0302: no analizar lo que no es código, no morir sin gcc."""

from pathlib import Path

import pytest

from rachel.core.analyzer import analizar_archivo_c, analizar_assembly_real
from rachel.core.masking import enmascarar_no_codigo

FUENTE = """#include <stdio.h>
/* Un switch comentado no es codigo:
switch (x) {
    case 1: break;
}
*/
const char *ayuda = "switch (y) { case 9: break; }";
#if 0
switch (z) {
    case 7: break;
}
#endif
int real(int v) {
    switch (v) {
        case 1: return 10;
        case 2: return 20;
        default: return 0;
    }
}
"""


@pytest.fixture
def archivo(tmp_path):
    ruta = tmp_path / "caso.c"
    ruta.write_text(FUENTE, encoding="utf-8")
    return ruta


def test_solo_se_detecta_el_switch_real(archivo):
    reporte = analizar_archivo_c(archivo)
    assert len(reporte.estructuras) == 1
    assert reporte.estructuras[0].casos[0].etiqueta == "1"


def test_el_enmascarado_preserva_offsets_y_lineas():
    enmascarado = enmascarar_no_codigo(FUENTE)
    assert len(enmascarado) == len(FUENTE)
    assert enmascarado.count("\n") == FUENTE.count("\n")


def test_el_switch_real_conserva_su_numero_de_linea(archivo):
    reporte = analizar_archivo_c(archivo)
    assert reporte.estructuras[0].linea_inicio == FUENTE.splitlines().index("    switch (v) {") + 1


def test_el_codigo_mostrado_es_el_original_no_el_enmascarado(archivo):
    """Lo que se le muestra al estudiante no puede venir blanqueado."""
    reporte = analizar_archivo_c(archivo)
    assert "return 10" in reporte.estructuras[0].codigo_fuente


@pytest.mark.parametrize(
    "fuente",
    [
        '// switch (a) { case 1: break; }\n',
        '/* switch (a) { case 1: break; } */\n',
        'char *s = "switch (a) { case 1: break; }";\n',
        '#if 0\nswitch (a) { case 1: break; }\n#endif\n',
    ],
)
def test_ningun_switch_inactivo_se_reporta(tmp_path, fuente):
    ruta = tmp_path / "inactivo.c"
    ruta.write_text(fuente, encoding="utf-8")
    assert analizar_archivo_c(ruta).estructuras == []


def test_if_0_con_else_deja_viva_la_rama_alternativa(tmp_path):
    ruta = tmp_path / "rama.c"
    ruta.write_text(
        "#if 0\n"
        "    switch (muerto) {\n        case 1: break;\n    }\n"
        "#else\n"
        "int f(int v) {\n"
        "    switch (v) {\n        case 1: return 1;\n        default: return 0;\n    }\n"
        "}\n"
        "#endif\n",
        encoding="utf-8",
    )
    estructuras = analizar_archivo_c(ruta).estructuras
    assert len(estructuras) == 1
    assert estructuras[0].casos[0].etiqueta == "1"


def test_sin_compilador_degrada_sin_traceback(archivo, monkeypatch):
    """RACHEL-D0302: antes reventaba con FileNotFoundError."""
    monkeypatch.setattr("rachel.core.analyzer.shutil.which", lambda _: None)
    assert analizar_assembly_real(archivo) == []
    reporte = analizar_archivo_c(archivo)
    assert len(reporte.estructuras) == 1
