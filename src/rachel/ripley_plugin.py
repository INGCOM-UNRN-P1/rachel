"""Adaptador de RACHEL para el protocolo de plugins de RIPLEY."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from rachel.core.analyzer import analizar_archivo_c


class RachelPlugin:
    """Expone el análisis de switches de RACHEL como observaciones JSON."""

    name = "rachel"
    version = "0.1.0"

    def is_available(self) -> bool:
        return True

    def execute(self, workspace: Path, manifest_config: Dict[str, Any]) -> Dict[str, Any]:
        observaciones = []
        reportes = []
        for archivo in sorted(Path(workspace).rglob("*.c")):
            reporte = analizar_archivo_c(archivo, manifest_config.get("opt_level", "-O2"))
            reportes.append(reporte.to_dict())
            for estructura in reporte.estructuras:
                if estructura.estrategia_compilacion != "sequential_cmp":
                    observaciones.append({
                        "rule_code": "RACHEL001",
                        "severity": "info",
                        "file": str(archivo),
                        "line": estructura.linea_inicio,
                        "message": (
                            f"Switch con estrategia {estructura.estrategia_compilacion} "
                            f"({len(estructura.casos)} casos)."
                        ),
                        "suggestion": estructura.explicacion_pedagogica,
                        "source_plugin": self.name,
                    })
        return {"ok": True, "observaciones": observaciones, "reportes": reportes}
