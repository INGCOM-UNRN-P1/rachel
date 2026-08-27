"""Tests de integración de la CLI de RACHEL."""

import json
from pathlib import Path
from typer.testing import CliRunner
from rachel.cli import app

runner = CliRunner()


def test_cli_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "RACHEL" in res.stdout


def test_cli_compare(tmp_path):
    fuente = tmp_path / "comp.c"
    fuente.write_text("int main(void) { return 0; }\n")

    res = runner.invoke(app, ["compare", str(fuente)])
    assert res.exit_code == 0
    assert "Comparativa" in res.stdout


def test_cli_switch_json(tmp_path):
    fuente = tmp_path / "sw.c"
    fuente.write_text("""
    int f(int x) {
        switch (x) {
            case 1: return 10;
            case 2: return 20;
            default: return 0;
        }
    }
    """)

    res = runner.invoke(app, ["switch", str(fuente), "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["total_switches"] == 1
    assert data["estructuras"][0]["cantidad_casos"] == 3
