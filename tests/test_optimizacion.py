"""Ola 19: -O0 contra -O2 explicado, cadenas de if-else que piden un switch y saltos en lenguaje de C."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rachel.cli import app
from rachel.core.masking import enmascarar_no_codigo
from rachel.core.optimizacion import (
    cadenas_if,
    comparar_optimizacion,
    desazucarar,
    evaluar_cadenas,
    metricas,
    _desenrollado,
)

runner = CliRunner()
necesita_gcc = pytest.mark.skipif(shutil.which("gcc") is None, reason="hace falta gcc")

DATOS = Path(__file__).parent


@necesita_gcc
def test_compare_opt_reconoce_las_transformaciones():
    por_funcion = {c.nombre: c for c in comparar_optimizacion(DATOS / "datos_opt.c")}
    assert por_funcion["cuadrado"].o2 is None  # static: se incorporó en su llamador
    assert any(t.startswith("Inlining: las llamadas a cuadrado()") for t in por_funcion["suma_cuadrados"].transformaciones)
    assert any(t.startswith("Recursión de cola") for t in por_funcion["mcd"].transformaciones)
    assert any(t.startswith("Lazo resuelto en tiempo de compilación") for t in por_funcion["suma_hasta_diez"].transformaciones)
    for c in por_funcion.values():
        if c.o2 is not None:
            assert c.o2.instrucciones <= c.o0.instrucciones
            assert any(t.startswith("Variables en registros") for t in c.transformaciones)


def test_metricas_y_desenrollado():
    cuerpo = [".L3:", "\taddl\t(%rdi), %eax", "\taddq\t$4, %rdi", "\taddl\t(%rdi), %eax", "\taddq\t$4, %rdi",
              "\tcmpq\t%rsi, %rdi", "\tjne\t.L3", "\tmovq\t-8(%rbp), %rax", "\tcall\tf", "\tcmovl\t%edx, %eax"]
    m = metricas(cuerpo)
    assert (m.instrucciones, m.saltos_condicionales, m.saltos_atras, m.llamadas, m.accesos_pila, m.cmov) == (9, 1, 1, ["f"], 1, 1)
    assert _desenrollado(cuerpo)
    assert not _desenrollado([".L3:", "\taddl\t$1, %eax", "\tcmpl\t$9, %eax", "\tjne\t.L3"])


def test_cadenas_sobre_la_misma_variable():
    fuente = (DATOS / "datos_opt.c").read_text(encoding="utf-8")
    cadenas = cadenas_if(fuente, enmascarar_no_codigo(fuente))
    assert [(c.funcion, c.variable, c.comparaciones, c.constantes) for c in cadenas] == [
        ("dia", "d", 6, ["1", "2", "3", "4", "5", "6"]),
        ("puntos", "carta", 5, ["1", "10", "12", "300", "-7"])]
    corta = "int f(int x)\n{\n    if (x == 1) return 1;\n    else if (x == 2) return 2;\n    return 0;\n}\n"
    assert cadenas_if(corta, enmascarar_no_codigo(corta)) == []
    mezcla = "int f(int x, int y)\n{\n" + "".join(
        f"    {'else ' if i else ''}if ({'x' if i % 2 else 'y'} == {i}) return {i};\n" for i in range(6)) + "    return 0;\n}\n"
    assert cadenas_if(mezcla, enmascarar_no_codigo(mezcla)) == []  # variables distintas: no es una cadena


@necesita_gcc
def test_cadenas_contra_el_assembly():
    por_funcion = {c.funcion: c for c in evaluar_cadenas(DATOS / "datos_opt.c")}
    assert por_funcion["puntos"].convertida_por_gcc is False
    assert "árbol de comparaciones" in por_funcion["puntos"].mensaje  # valores dispersos
    res = runner.invoke(app, ["cadenas", str(DATOS / "datos_opt.c"), "--json"])
    assert res.exit_code == 1 and {c["funcion"] for c in json.loads(res.stdout)["cadenas_if"]} == {"dia", "puntos"}


@necesita_gcc
def test_desazucarar():
    texto = desazucarar(DATOS / "datos_cond.c")
    assert "# ── línea 3: if (x > 5)" in texto
    assert "# salta a .L2 si x <= 5: es decir, cuando «x > 5» es falsa" in texto
    assert "si u > 2 (sin signo): es decir, cuando «u < 3» es falsa" in texto
    assert "si x != 10: es decir, cuando «x != 10» es verdadera" in texto
    res = runner.invoke(app, ["desazucarar", str(DATOS / "datos_cond.c"), "-f", "nada"])
    assert res.exit_code == 2


@necesita_gcc
def test_compare_opt_cli_json():
    res = runner.invoke(app, ["compare-opt", str(DATOS / "datos_opt.c"), "--json"])
    assert res.exit_code == 0
    datos = json.loads(res.stdout)
    assert {f["nombre"] for f in datos["funciones"]} >= {"cuadrado", "mcd", "dia"}


@necesita_gcc
def test_vectorizacion_y_desenrollado_con_o3():
    suma = next(c for c in comparar_optimizacion(DATOS / "datos_opt.c", "-O3") if c.nombre == "suma_cuadrados")
    assert suma.o2 is not None and suma.o2.simd > 0
    assert any(t.startswith("Vectorización") for t in suma.transformaciones)
