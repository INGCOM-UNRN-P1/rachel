"""Modelos de datos para el análisis de estructuras de control y jump tables en RACHEL."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# estrategia -> (nombre, complejidad, color de la terminal)
ESTRATEGIAS = {
    "jump_table": ("Tabla de Saltos (Jump Table)", "O(1)", "green"),
    "sin_saltos": ("Resuelto sin saltos (aritmética o cmov)", "O(1)", "green"),
    "binary_tree_cmp": ("Árbol Binario", "O(log N)", "yellow"),
    "sequential_cmp": ("Secuencial", "O(N)", "blue"),
}


@dataclass
class CasoSwitch:
    """Representa una rama 'case' en un switch."""
    etiqueta: str               # "1", "2", "'a'", "default"
    linea: int
    es_default: bool = False
    tiene_break: bool = True


@dataclass
class EstructuraControl:
    """Diagnóstico de compilación y flujo de control para una estructura en C."""
    tipo: str                   # "switch", "if_else", "for", "while", "do_while"
    funcion: str
    linea_inicio: int
    linea_fin: int
    codigo_fuente: str
    casos: List[CasoSwitch] = field(default_factory=list)
    estrategia_compilacion: str = "sequential_cmp"  # ver ESTRATEGIAS
    verificado_con_assembly: bool = False           # True si el assembly real confirmó o corrigió la predicción
    densidad_casos: float = 1.0                     # Ratio casos / (max - min + 1)
    instrucciones_assembly: List[str] = field(default_factory=list)
    diagrama_mermaid: str = ""
    explicacion_pedagogica: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tipo": self.tipo,
            "funcion": self.funcion,
            "linea_inicio": self.linea_inicio,
            "linea_fin": self.linea_fin,
            "cantidad_casos": len(self.casos),
            "estrategia_compilacion": self.estrategia_compilacion,
            "verificado_con_assembly": self.verificado_con_assembly,
            "densidad_casos": self.densidad_casos,
            "instrucciones_assembly": self.instrucciones_assembly[:15],
            "diagrama_mermaid": self.diagrama_mermaid,
            "explicacion_pedagogica": self.explicacion_pedagogica,
        }


@dataclass
class ReporteEstructuras:
    """Reporte consolidado de todas las estructuras de control de un archivo."""
    archivo: Path
    estructuras: List[EstructuraControl] = field(default_factory=list)

    @property
    def total_switches(self) -> int:
        return sum(1 for e in self.estructuras if e.tipo == "switch")

    @property
    def total_jump_tables(self) -> int:
        return sum(1 for e in self.estructuras if e.estrategia_compilacion == "jump_table")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "archivo": str(self.archivo),
            "total_estructuras": len(self.estructuras),
            "total_switches": self.total_switches,
            "total_jump_tables": self.total_jump_tables,
            "estructuras": [e.to_dict() for e in self.estructuras],
        }
