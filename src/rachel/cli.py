"""CLI de RACHEL — Desensamblador y visualizador pedagógico de estructuras de control y jump tables."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from rachel import __version__
from rachel.core.analyzer import analizar_archivo_c

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="rachel",
    help="⚡ RACHEL — Desensamblador y visualizador pedagógico de estructuras de control y jump tables en C.",
    add_completion=True,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]RACHEL[/bold cyan] versión [bold]{__version__}[/bold]")
        raise typer.Exit(code=0)


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Muestra la versión de RACHEL.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    pass


def generar_seccion_markdown(reporte) -> str:
    """Genera sección de análisis de control de flujo y switch/jump tables para Dredd."""
    lines = ["## Desensamblado y Control de Flujo (Rachel)\n"]
    lines.append(f"- **Archivo analizado:** `{reporte.archivo.name}`")
    lines.append(f"- **Sentencias switch analizadas:** {len(reporte.estructuras)}\n")
    if not reporte.estructuras:
        lines.append("> [!NOTE]\n> No se encontraron sentencias `switch` en el código fuente analizado.\n")
    else:
        lines.append("| Función | Líneas | Casos | Estrategia Ensamblador | Complejidad |")
        lines.append("| :--- | :---: | :---: | :--- | :---: |")
        for e in reporte.estructuras:
            est_nombre = "Tabla de Saltos (Jump Table)" if e.estrategia_compilacion == "jump_table" else "Árbol Binario" if e.estrategia_compilacion == "binary_tree_cmp" else "Secuencial"
            comp_nombre = "O(1)" if e.estrategia_compilacion == "jump_table" else "O(log N)" if e.estrategia_compilacion == "binary_tree_cmp" else "O(N)"
            lines.append(f"| `{e.funcion}()` | {e.linea_inicio}-{e.linea_fin} | {len(e.casos)} | {est_nombre} | **{comp_nombre}** |")
        lines.append("")
    return "\n".join(lines)


@app.command("switch")
@app.command("check")
def switch_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a desensamblar e inspeccionar."),
    opt: str = typer.Option("-O2", "--opt", "-O", help="Nivel de optimización de GCC (-O0, -O1, -O2, -O3, -Os)."),
    mermaid_view: bool = typer.Option(False, "--mermaid", "-m", help="Emitir diagrama de flujo en sintaxis Mermaid."),
    json_output: bool = typer.Option(False, "--json", help="Emitir reporte en formato JSON."),
    output_md: Optional[Path] = typer.Option(None, "--md", "--output-md", "-o", help="Generar sección de reporte en formato Markdown para fusión en Dredd."),
) -> None:
    """Analiza las sentencias switch del código C, visualiza su diagrama de flujo y desensambla jump tables."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)

    reporte = analizar_archivo_c(fuente, opt_level=opt)

    if output_md:
        md_text = generar_seccion_markdown(reporte)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md_text, encoding="utf-8")
        console.print(f"[green]✓ Sección Markdown generada en:[/green] [cyan]{output_md}[/cyan]")
        raise typer.Exit(code=0)

    if json_output:
        print(json.dumps(reporte.to_dict(), indent=2, ensure_ascii=False))
        raise typer.Exit(code=0)

    if not reporte.estructuras:
        console.print(f"[yellow]No se encontraron sentencias 'switch' en {fuente.name}.[/yellow]")
        raise typer.Exit(code=0)

    if mermaid_view:
        for e in reporte.estructuras:
            console.print(f"%% Diagrama de switch en {e.funcion}() (Línea {e.linea_inicio})")
            console.print(e.diagrama_mermaid + "\n")
        raise typer.Exit(code=0)

    console.print(f"\n[bold]⚡ Análisis de Sentencias Switch en {fuente.name}:[/bold]\n")

    for idx, e in enumerate(reporte.estructuras, 1):
        color_est = "green" if e.estrategia_compilacion == "jump_table" else "yellow" if e.estrategia_compilacion == "binary_tree_cmp" else "blue"
        est_nombre = "Tabla de Saltos O(1)" if e.estrategia_compilacion == "jump_table" else "Árbol Binario O(log N)" if e.estrategia_compilacion == "binary_tree_cmp" else "Comparación Secuencial O(N)"

        resumen = (
            f"• Función: [bold cyan]{e.funcion}[/bold cyan] (Líneas {e.linea_inicio} a {e.linea_fin})\n"
            f"• Cantidad de casos: [bold]{len(e.casos)}[/bold] (Densidad de claves: [bold]{e.densidad_casos:.2f}[/bold])\n"
            f"• Estrategia de compilación GCC ({opt}): [{color_est}][bold]{est_nombre}[/bold][/{color_est}]\n"
            f"• Explicación: {e.explicacion_pedagogica}"
        )
        console.print(Panel(resumen, title=f"Switch #{idx} en {e.funcion}()", border_style="cyan"))

        # Casos
        tabla_casos = Table(title="Detalle de Casos")
        tabla_casos.add_column("Caso / Etiqueta", style="bold yellow")
        tabla_casos.add_column("Línea", justify="center")
        tabla_casos.add_column("Tipo", justify="center")

        for c in e.casos:
            tipo_caso = "[dim]default[/dim]" if c.es_default else "case constante"
            tabla_casos.add_row(c.etiqueta, str(c.linea), tipo_caso)

        console.print(tabla_casos)

        # Fragmento de Assembly si existe
        if e.instrucciones_assembly:
            asm_snippet = "\n".join(e.instrucciones_assembly[:12])
            console.print(Panel(
                Syntax(asm_snippet, "asm", theme="monokai", line_numbers=True),
                title=f"🔬 Fragmento Assembly ({opt})",
                border_style="dim",
            ))


@app.command("compare")
def compare_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a comparar."),
) -> None:
    """Compara el costo computacional entre la implementación de switch vs cadenas de if-else."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)

    reporte = analizar_archivo_c(fuente)
    tabla = Table(title="Comparativa de Flujo: Switch vs If-Else")
    tabla.add_column("Métrica / Aspecto", style="bold cyan")
    tabla.add_column("Switch con Jump Table", style="green")
    tabla.add_column("Cadena if-else if", style="yellow")

    tabla.add_row("Complejidad Temporal", "O(1) constante", "O(N) lineal en peor caso")
    tabla.add_row("Branch Prediction", "1 salto indirecto (jmp *reg)", "N saltos condicionales sucesivos")
    tabla.add_row("Consumo de Memoria", "Tabla de punteros en .rodata", "Código de instrucciones lineal")
    tabla.add_row("Requisito", "Valores enteros/constantes", "Cualquier expresión booleana")

    console.print(tabla)


@app.command("report")
def report_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a desensamblar."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de destino del archivo Markdown."),
    opt: str = typer.Option("-O2", "--opt", "-O", help="Nivel de optimización."),
) -> None:
    """Genera directamente la sección de reporte Markdown de RACHEL para Dredd."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)
    reporte = analizar_archivo_c(fuente, opt_level=opt)
    md_content = generar_seccion_markdown(reporte)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md_content, encoding="utf-8")
        console.print(f"[green]✓ Reporte Markdown generado en:[/green] [cyan]{output}[/cyan]")
    else:
        print(md_content)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
