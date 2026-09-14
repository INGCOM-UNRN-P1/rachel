from pathlib import Path

from rachel.ripley_plugin import RachelPlugin


def test_rachel_plugin_contract(tmp_path: Path, monkeypatch):
    fuente = tmp_path / "main.c"
    fuente.write_text("int main(void) { return 0; }\n", encoding="utf-8")
    monkeypatch.setattr(
        "rachel.ripley_plugin.analizar_archivo_c",
        lambda archivo, opt_level: type(
            "Reporte",
            (),
            {"estructuras": [], "to_dict": lambda self: {"archivo": str(archivo)}},
        )(),
    )

    resultado = RachelPlugin().execute(tmp_path, {})

    assert RachelPlugin().is_available()
    assert resultado["ok"] is True
    assert resultado["observaciones"] == []
