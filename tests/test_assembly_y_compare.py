"""Regresión de RACHEL-D0303/D0304.

D0303: cada switch recibía las primeras 25 líneas del assembly del archivo
COMPLETO (idénticas para todos), y la tabla de saltos se confirmaba con un `jmp *`
de cualquier función.
D0304: `compare` descartaba el análisis y imprimía una tabla fija.
"""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rachel.cli import app
from rachel.core.analyzer import analizar_archivo_c, extraer_assembly_de_funcion

runner = CliRunner()
necesita_gcc = pytest.mark.skipif(not shutil.which("gcc"), reason="requiere gcc")

DOS_SWITCHES = """int denso(int c) {
    switch (c) {
        case 0: return 10;
        case 1: return 20;
        case 2: return 30;
        case 3: return 40;
        case 4: return 50;
        case 5: return 60;
        default: return 0;
    }
}
int disperso(int c) {
    switch (c) {
        case 1: return 5;
        case 1000: return 6;
        default: return 0;
    }
}
int main(void) { return denso(2) + disperso(1000); }
"""


def test_extraer_assembly_de_funcion_aisla_una_sola():
    # Las líneas llegan ya sin sangrado inicial: `analizar_assembly_real` hace `strip()`.
    asm = [".text", "uno:", "ret", ".size\tuno, .-uno", "dos:", "jmp\t*%rax", ".size\tdos, .-dos"]
    assert extraer_assembly_de_funcion(asm, "uno") == ["uno:", "ret"]
    assert extraer_assembly_de_funcion(asm, "dos") == ["dos:", "jmp\t*%rax"]
    assert extraer_assembly_de_funcion(asm, "no_existe") == []


@necesita_gcc
def test_cada_switch_recibe_el_assembly_de_su_propia_funcion(tmp_path):
    ruta = tmp_path / "dos.c"
    ruta.write_text(DOS_SWITCHES, encoding="utf-8")
    por_funcion = {e.funcion: e for e in analizar_archivo_c(ruta).estructuras}

    assert por_funcion["denso"].instrucciones_assembly[0] == "denso:"
    assert por_funcion["disperso"].instrucciones_assembly[0] == "disperso:"
    assert por_funcion["denso"].instrucciones_assembly != por_funcion["disperso"].instrucciones_assembly


def test_un_jmp_de_otra_funcion_no_confirma_la_tabla_de_saltos():
    """La detección se acota al assembly de la función del switch."""
    otra = ["otra:", "jmp\t*%rax", ".size\totra, .-otra", "esta:", "ret", ".size\testa, .-esta"]
    mia = extraer_assembly_de_funcion(otra, "esta")
    assert not any("jmp" in l and "*" in l for l in mia)


@necesita_gcc
def test_compare_muestra_los_switch_reales_del_archivo(tmp_path):
    ruta = tmp_path / "dos.c"
    ruta.write_text(DOS_SWITCHES, encoding="utf-8")
    res = runner.invoke(app, ["compare", str(ruta)])
    assert res.exit_code == 0
    assert "denso" in res.output and "disperso" in res.output


def test_compare_sin_switch_no_imprime_una_tabla_inventada(tmp_path):
    ruta = tmp_path / "sin.c"
    ruta.write_text("int main(void) { return 0; }\n", encoding="utf-8")
    res = runner.invoke(app, ["compare", str(ruta)])
    assert res.exit_code == 0
    assert "no hay nada que comparar" in res.output
    assert "Jump Table" not in res.output


@necesita_gcc
def test_compare_distingue_dos_archivos_distintos(tmp_path):
    """Antes la salida era idéntica para cualquier entrada."""
    a = tmp_path / "a.c"
    a.write_text(DOS_SWITCHES, encoding="utf-8")
    b = tmp_path / "b.c"
    b.write_text("int f(int c) { switch (c) { case 1: return 1; default: return 0; } }\nint main(void){return f(1);}\n", encoding="utf-8")
    assert runner.invoke(app, ["compare", str(a)]).output != runner.invoke(app, ["compare", str(b)]).output
