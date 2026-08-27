"""Tests adicionales para maximizar la cobertura en RACHEL."""

import json
from pathlib import Path
from typer.testing import CliRunner
import rachel.cli
from rachel.cli import app
from rachel.core.analyzer import analizar_archivo_c

runner = CliRunner()


def test_cli_switch_rich_and_mermaid(tmp_path):
    fuente = tmp_path / "switch.c"
    fuente.write_text("""
    int procesar(int op) {
        int r = 0;
        switch (op) {
            case 1: r = 10; break;
            case 2: r = 20; break;
            case 3: r = 30; break;
            case 4: r = 40; break;
            case 5: r = 50; break;
            default: r = -1; break;
        }
        return r;
    }
    """)

    # Rich view
    res_rich = runner.invoke(app, ["switch", str(fuente)])
    assert res_rich.exit_code == 0
    assert "Análisis de Sentencias Switch" in res_rich.stdout

    # Mermaid view
    res_m = runner.invoke(app, ["switch", str(fuente), "--mermaid"])
    assert res_m.exit_code == 0
    assert "graph TD" in res_m.stdout


def test_cli_switch_sin_switches(tmp_path):
    fuente = tmp_path / "noswitch.c"
    fuente.write_text("int f(int x) { return x + 1; }\n")

    res = runner.invoke(app, ["switch", str(fuente)])
    assert res.exit_code == 0
    assert "No se encontraron" in res.stdout


def test_cli_compare(tmp_path):
    fuente = tmp_path / "sample.c"
    fuente.write_text("int f() { return 1; }\n")

    res = runner.invoke(app, ["compare", str(fuente)])
    assert res.exit_code == 0
    assert "Comparativa de Flujo" in res.stdout


def test_cli_file_not_found():
    res1 = runner.invoke(app, ["switch", "/no/existe.c"])
    assert res1.exit_code == 2

    res2 = runner.invoke(app, ["compare", "/no/existe.c"])
    assert res2.exit_code == 2


def test_cli_main_block(monkeypatch):
    monkeypatch.setattr("sys.argv", ["rachel", "--version"])
    try:
        rachel.cli.main()
    except SystemExit as e:
        assert e.code == 0
