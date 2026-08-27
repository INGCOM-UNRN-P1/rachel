"""Tests unitarios para el analizador de estructuras y jump tables en RACHEL."""

from pathlib import Path
import pytest
from rachel.core.analyzer import analizar_archivo_c, extraer_switches_c


def test_extraer_switch_basico(tmp_path):
    """Verifica la extracción y conteo de casos en un switch simple."""
    fuente = tmp_path / "switch.c"
    fuente.write_text("""
    int procesar_opcion(int op) {
        int r = 0;
        switch (op) {
            case 1:
                r = 10;
                break;
            case 2:
                r = 20;
                break;
            case 3:
                r = 30;
                break;
            default:
                r = -1;
                break;
        }
        return r;
    }
    """)
    switches = extraer_switches_c(fuente.read_text(), fuente)
    assert len(switches) == 1
    s = switches[0]
    assert s.funcion == "procesar_opcion"
    assert len(s.casos) == 4
    assert any(c.es_default for c in s.casos)


def test_analisis_completo_con_assembly(tmp_path):
    """Verifica el análisis integral con desensamblado de GCC."""
    fuente = tmp_path / "jump_table.c"
    fuente.write_text("""
    int ejecutar_comando(int cmd) {
        switch (cmd) {
            case 0: return 100;
            case 1: return 200;
            case 2: return 300;
            case 3: return 400;
            case 4: return 500;
            case 5: return 600;
            default: return -1;
        }
    }
    """)
    rep = analizar_archivo_c(fuente, opt_level="-O2")
    assert rep.total_switches == 1
    s = rep.estructuras[0]
    assert s.estrategia_compilacion in ("jump_table", "binary_tree_cmp", "sequential_cmp")
    assert "graph TD" in s.diagrama_mermaid
