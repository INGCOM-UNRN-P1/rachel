"""Regresión de RACHEL-D0306: la predicción por densidad nunca se refutaba con el assembly real.

`denso(int c)` con 7 casos consecutivos que devuelven constantes se reportaba como
"Tabla de Saltos O(1)", pero `gcc -O2` lo compila a `lea` + `cmov` sin ningún salto. Solo se
*promovía* a jump_table ante un `jmp *`; si no aparecía, la predicción quedaba intacta.
"""

import shutil

import pytest

from rachel.core.analyzer import _refutar_o_confirmar, analizar_archivo_c
from rachel.core.models import CasoSwitch, EstructuraControl

necesita_gcc = pytest.mark.skipif(not shutil.which("gcc"), reason="requiere gcc")


def _switch(n_casos: int, estrategia: str, densidad: float = 1.0) -> EstructuraControl:
    return EstructuraControl(
        tipo="switch", funcion="f", linea_inicio=1, linea_fin=9, codigo_fuente="",
        casos=[CasoSwitch(etiqueta=str(i), linea=i) for i in range(n_casos)],
        estrategia_compilacion=estrategia, densidad_casos=densidad,
        explicacion_pedagogica="predicción",
    )


TABLA = ["f:", "cmpl\t$6, %edi", "ja\t.L2", "jmp\t*.L4(,%rdi,8)", ".L2:", "ret"]
ARITMETICA = ["f:", "leal\t5(%rdi,%rdi,4), %eax", "cmpl\t$6, %edi", "cmovbe\t%eax, %edx", "ret"]
COMPARACIONES = ["f:", "cmpl\t$3, %edi", "je\t.L3", "cmpl\t$5, %edi", "je\t.L4", "jmp\t.L2", ".L2:", "ret"]


def test_un_salto_indirecto_confirma_la_tabla():
    s = _switch(7, "sequential_cmp")
    _refutar_o_confirmar(s, TABLA, "-O2")
    assert s.estrategia_compilacion == "jump_table"
    assert "Verificado por GCC" in s.explicacion_pedagogica


def test_sin_ningun_salto_no_es_una_tabla_sino_aritmetica():
    s = _switch(7, "jump_table")
    _refutar_o_confirmar(s, ARITMETICA, "-O2")
    assert s.estrategia_compilacion == "sin_saltos"
    assert "SIN ninguna instrucción de salto" in s.explicacion_pedagogica
    assert "no hay tabla de saltos" in s.explicacion_pedagogica


def test_una_tabla_prevista_que_gcc_no_genero_se_degrada_a_comparaciones():
    s = _switch(7, "jump_table")
    _refutar_o_confirmar(s, COMPARACIONES, "-O2")
    assert s.estrategia_compilacion == "binary_tree_cmp"
    assert "no tiene ningún salto indirecto" in s.explicacion_pedagogica
    chico = _switch(4, "jump_table")
    _refutar_o_confirmar(chico, COMPARACIONES, "-O2")
    assert chico.estrategia_compilacion == "sequential_cmp"


def test_una_prediccion_de_comparaciones_coherente_con_el_assembly_no_cambia():
    s = _switch(3, "sequential_cmp")
    _refutar_o_confirmar(s, COMPARACIONES, "-O2")
    assert s.estrategia_compilacion == "sequential_cmp"
    assert s.explicacion_pedagogica == "predicción"


@necesita_gcc
def test_el_caso_del_hallazgo_con_gcc_real(tmp_path):
    fuente = tmp_path / "denso.c"
    fuente.write_text(
        "int denso(int c) {\n    switch (c) {\n"
        "        case 0: return 5; case 1: return 10; case 2: return 15; case 3: return 20;\n"
        "        case 4: return 25; case 5: return 30; case 6: return 35;\n"
        "        default: return 0;\n    }\n}\n"
        "int main(void) { return denso(2); }\n",
        encoding="utf-8",
    )
    switch = analizar_archivo_c(fuente, opt_level="-O2").estructuras[0]
    assert switch.verificado_con_assembly is True
    assert switch.estrategia_compilacion != "jump_table" or any(
        "jmp" in l and "*" in l for l in switch.instrucciones_assembly
    )
    assert switch.estrategia_compilacion in ("sin_saltos", "binary_tree_cmp")


@necesita_gcc
def test_la_cli_muestra_la_estrategia_real_y_no_la_prevista(tmp_path):
    from typer.testing import CliRunner
    from rachel.cli import app

    fuente = tmp_path / "denso.c"
    fuente.write_text(
        "int denso(int c) {\n    switch (c) {\n"
        "        case 0: return 5; case 1: return 10; case 2: return 15; case 3: return 20;\n"
        "        case 4: return 25; case 5: return 30; case 6: return 35;\n"
        "        default: return 0;\n    }\n}\n",
        encoding="utf-8",
    )
    res = CliRunner().invoke(app, ["check", str(fuente)])
    assert any(t in res.output for t in ("Resuelto sin saltos", "Árbol Binario de Comparaciones", "binary_tree_cmp"))
    assert "Tabla de Saltos O(1)" not in res.output


def test_el_json_indica_si_el_assembly_verifico_la_prediccion(tmp_path):
    fuente = tmp_path / "s.c"
    fuente.write_text("int f(int c) {\n    switch (c) {\n        case 1: return 1;\n        case 2: return 4;\n        case 3: return 9;\n        default: return 0;\n    }\n}\n", encoding="utf-8")
    rep = analizar_archivo_c(fuente)
    assert "verificado_con_assembly" in rep.estructuras[0].to_dict()
