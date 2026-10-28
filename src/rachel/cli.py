"""CLI de RACHEL — Desensamblador y visualizador pedagógico de estructuras de control y jump tables."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Optional

import typer
from yutani.cli import crear_app
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from rachel import __version__
from rachel.core.analyzer import analizar_archivo_c, validar_opt_level
from rachel.core.models import ESTRATEGIAS

console = Console()
err_console = Console(stderr=True)

# Contrato de línea de comandos del ecosistema (-h/--help, --version/-v, errores de datos como
# mensajes) y textos de Typer en español, desde yutani (N-ECO-14).
app = crear_app(
    "rachel",
    __version__,
    "⚡ RACHEL — Desensamblador y visualizador pedagógico de estructuras de control y jump tables en C.",
    add_completion=True,
)


def generar_seccion_markdown(reporte) -> str:
    """Genera sección de análisis de control de flujo y switch/jump tables para Dredd."""
    status = "ok"
    lines = [
        f"<!-- dredd-section: rachel, tool=rachel, version=1.0.0, status={status} -->\n",
        "## Desensamblado y Control de Flujo (Rachel)\n",
    ]
    lines.append(f"- **Archivo analizado:** `{reporte.archivo.name}`")
    lines.append(f"- **Sentencias switch analizadas:** {len(reporte.estructuras)}\n")
    if not reporte.estructuras:
        lines.append("> [!NOTE]\n> No se encontraron sentencias `switch` en el código fuente analizado.\n")
    else:
        lines.append("| Función | Líneas | Casos | Estrategia Ensamblador | Complejidad |")
        lines.append("| :--- | :---: | :---: | :--- | :---: |")
        for e in reporte.estructuras:
            est_nombre, comp_nombre, _ = ESTRATEGIAS.get(e.estrategia_compilacion, ESTRATEGIAS["sequential_cmp"])
            fn_limpia = e.funcion.replace("|", "&#124;")
            lines.append(f"| `{fn_limpia}()` | {e.linea_inicio}-{e.linea_fin} | {len(e.casos)} | {est_nombre} | **{comp_nombre}** |")
        lines.append("")
    for c in reporte.cadenas_if:
        tipo = "NOTE" if c.convertida_por_gcc else "WARNING"
        lines.append(f"> [!{tipo}]\n> **Cadena de if-else en `{c.funcion}()`:** {c.mensaje}\n")
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

    try:
        validar_opt_level(opt)
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=2) from e
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
        for est in reporte.estructuras:
            console.print(f"%% Diagrama de switch en {est.funcion}() (Línea {est.linea_inicio})")
            console.print(est.diagrama_mermaid + "\n")
        raise typer.Exit(code=0)

    console.print(f"\n[bold]⚡ Análisis de Sentencias Switch en {fuente.name}:[/bold]\n")

    for idx, est in enumerate(reporte.estructuras, 1):
        nombre_e, complejidad_e, color_est = ESTRATEGIAS.get(est.estrategia_compilacion, ESTRATEGIAS["sequential_cmp"])
        est_nombre = f"{nombre_e} {complejidad_e}"

        resumen = (
            f"• Función: [bold cyan]{est.funcion}[/bold cyan] (Líneas {est.linea_inicio} a {est.linea_fin})\n"
            f"• Cantidad de casos: [bold]{len(est.casos)}[/bold] (Densidad de claves: [bold]{est.densidad_casos:.2f}[/bold])\n"
            f"• Estrategia de compilación GCC ({opt}): [{color_est}][bold]{est_nombre}[/bold][/{color_est}]\n"
            f"• Explicación: {est.explicacion_pedagogica}"
        )
        console.print(Panel(resumen, title=f"Switch #{idx} en {est.funcion}()", border_style="cyan"))

        # Casos
        tabla_casos = Table(title="Detalle de Casos")
        tabla_casos.add_column("Caso / Etiqueta", style="bold yellow")
        tabla_casos.add_column("Línea", justify="center")
        tabla_casos.add_column("Tipo", justify="center")

        for c in est.casos:
            tipo_caso = "[dim]default[/dim]" if c.es_default else "case constante"
            tabla_casos.add_row(c.etiqueta, str(c.linea), tipo_caso)

        console.print(tabla_casos)

        # Fragmento de Assembly si existe
        if est.instrucciones_assembly:
            asm_snippet = "\n".join(est.instrucciones_assembly[:12])
            console.print(Panel(
                Syntax(asm_snippet, "asm", theme="monokai", line_numbers=True),
                title=f"🔬 Fragmento Assembly ({opt})",
                border_style="dim",
            ))


def _o_salir(funcion, *args, **kwargs):
    from rachel.core.optimizacion import SinCompilador

    try:
        return funcion(*args, **kwargs)
    except (SinCompilador, ValueError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


@app.command("compare-opt")
def compare_opt_cmd(
    fuente: Path = typer.Argument(..., exists=True, dir_okay=False, help="Archivo C a compilar con -O0 y con -O2."),
    opt: str = typer.Option("-O2", "--opt", "-O", help="Nivel con el que se compara -O0 (-O1, -O2, -O3, -Os)."),
    json_output: bool = typer.Option(False, "--json", help="Emitir la comparación en JSON."),
) -> None:
    """Compara el assembly de -O0 y -O2 por función y explica en español qué transformó el optimizador.

    Instrucciones, saltos condicionales, llamadas y accesos a la pila de cada versión, y las transformaciones
    reconocidas: inlining, variables en registros, vectorización, desenrollado, saltos reemplazados por cmov,
    recursión de cola convertida en lazo y lazos resueltos en tiempo de compilación.
    """
    from rachel.core.optimizacion import comparar_optimizacion

    comparacion = _o_salir(comparar_optimizacion, fuente, opt)
    if json_output:
        print(json.dumps({"schema_version": "1.0.0", "archivo": str(fuente), "opt": opt, "funciones": [
            {"nombre": c.nombre, "O0": vars(c.o0), opt.lstrip("-"): vars(c.o2) if c.o2 else None,
             "transformaciones": c.transformaciones} for c in comparacion]}, indent=2, ensure_ascii=False))
        return
    tabla = Table(title=f"-O0 contra {opt} ({fuente.name})")
    for col in ("Función", "Instrucciones", "Saltos condicionales", "Llamadas", "Accesos a la pila"):
        tabla.add_column(col, justify="left" if col == "Función" else "right")

    def par(a: int, b: Optional[int]) -> str:
        return f"{a} → {b}" if b is not None else f"{a} → (incorporada)"

    for c in comparacion:
        o2 = c.o2
        tabla.add_row(f"{c.nombre}()", par(c.o0.instrucciones, o2.instrucciones if o2 else None),
                      par(c.o0.saltos_condicionales, o2.saltos_condicionales if o2 else None),
                      par(len(c.o0.llamadas), len(o2.llamadas) if o2 else None),
                      par(c.o0.accesos_pila, o2.accesos_pila if o2 else None))
    console.print(tabla)
    for c in comparacion:
        if c.transformaciones:
            console.print(f"\n[bold cyan]{c.nombre}()[/bold cyan]")
            for t in c.transformaciones:
                console.print(f"  • {t}")


@app.command("cadenas")
def cadenas_cmd(
    fuente: Path = typer.Argument(..., exists=True, dir_okay=False, help="Archivo C a revisar."),
    opt: str = typer.Option("-O2", "--opt", "-O", help="Nivel de optimización con que se mira el assembly."),
    json_output: bool = typer.Option(False, "--json", help="Emitir en JSON."),
) -> None:
    """Cadenas de if / else if de más de 4 comparaciones con constantes, que conviene escribir como switch.

    Con el assembly se distingue la cadena que GCC ya convirtió en una tabla de la que quedó como una
    comparación tras otra. Sale con 1 si hay alguna de estas últimas.
    """
    from rachel.core.optimizacion import evaluar_cadenas

    cadenas = _o_salir(evaluar_cadenas, fuente, opt)
    if json_output:
        print(json.dumps({"schema_version": "1.0.0", "archivo": str(fuente), "cadenas_if": [vars(c) for c in cadenas]},
                         indent=2, ensure_ascii=False))
    elif not cadenas:
        console.print(f"[green]{fuente.name}: no hay cadenas de if-else de más de 4 comparaciones con constantes.[/green]")
    else:
        for c in cadenas:
            color = "cyan" if c.convertida_por_gcc else "yellow"
            console.print(f"[{color}]{fuente.name}:{c.linea_inicio} ({c.funcion}):[/{color}] {c.mensaje}")
    raise typer.Exit(code=1 if any(not c.convertida_por_gcc for c in cadenas) else 0)


@app.command("desazucarar")
def desazucarar_cmd(
    fuente: Path = typer.Argument(..., exists=True, dir_okay=False, help="Archivo C a desensamblar."),
    funcion: Optional[str] = typer.Option(None, "--funcion", "-f", help="Sólo esta función."),
    opt: str = typer.Option("-O0", "--opt", "-O", help="Nivel de optimización (con -O0 cada if se ve tal cual)."),
) -> None:
    """Assembly anotado: cada cmp/test y salto condicional con la condición en C que evalúa.

    `jle .L2` después de `cmpl $5, -4(%rbp)` se lee «salta a .L2 si x <= 5: es decir, cuando «x > 5» es
    falsa». Los nombres de las variables y las líneas de C salen de gcc -fverbose-asm.
    """
    from rachel.core.optimizacion import desazucarar

    texto = _o_salir(desazucarar, fuente, opt, funcion)
    if funcion and not texto.strip():
        err_console.print(f"[red]Error:[/red] no hay una función {funcion}() en {fuente.name}.")
        raise typer.Exit(code=2)
    print(texto, end="")


@app.command("compare")
def compare_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a comparar."),
) -> None:
    """Compara el costo computacional entre la implementación de switch vs cadenas de if-else."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)

    reporte = analizar_archivo_c(fuente)

    # Antes se descartaba `reporte` y se imprimía una tabla fija idéntica para
    # cualquier archivo, con la columna "Switch con Jump Table" aun si el fuente
    # no tenía ni un switch. Ahora se compara cada switch REAL contra lo que le
    # costaría la cadena if-else equivalente.
    if not reporte.estructuras:
        console.print(f"[yellow]No se encontraron sentencias switch en {fuente.name}: no hay nada que comparar.[/yellow]")
        raise typer.Exit(code=0)

    tabla = Table(title=f"Comparativa de Flujo: Switch vs If-Else ({fuente.name})")
    tabla.add_column("Función", style="bold cyan")
    tabla.add_column("Línea", justify="right")
    tabla.add_column("Casos", justify="right")
    tabla.add_column("Densidad", justify="right")
    tabla.add_column("Estrategia del compilador", style="green")
    tabla.add_column("Switch (comparaciones)", style="green")
    tabla.add_column("Cadena if-else (peor caso)", style="yellow")

    for e in reporte.estructuras:
        n = len(e.casos)
        if e.estrategia_compilacion == "jump_table":
            estrategia, costo_switch = "Tabla de Saltos", "1 salto indirecto, O(1)"
        elif e.estrategia_compilacion == "sin_saltos":
            estrategia, costo_switch = "Sin saltos (cmov)", "0 saltos, O(1)"
        elif e.estrategia_compilacion == "binary_tree_cmp":
            estrategia, costo_switch = "Árbol Binario", f"~{max(1, math.ceil(math.log2(max(n, 2))))} comparaciones, O(log N)"
        else:
            estrategia, costo_switch = "Secuencial", f"hasta {n} comparaciones, O(N)"
        tabla.add_row(
            e.funcion, str(e.linea_inicio), str(n), f"{e.densidad_casos:.2f}",
            estrategia, costo_switch, f"hasta {n} comparaciones, O(N)",
        )

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
    try:
        validar_opt_level(opt)
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=2) from e
    reporte = analizar_archivo_c(fuente, opt_level=opt)
    md_content = generar_seccion_markdown(reporte)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md_content, encoding="utf-8")
        console.print(f"[green]✓ Reporte Markdown generado en:[/green] [cyan]{output}[/cyan]")
    else:
        print(md_content)


@app.command("doctor")
def doctor_cmd(
    json_output: bool = typer.Option(False, "--json", help="Emitir diagnóstico en formato JSON estructurado."),
) -> None:
    """Verifica el estado del entorno de RACHEL (Python, GCC, objdump)."""
    import shutil
    import sys
    diagnostico = []

    py_ok = sys.version_info >= (3, 10)
    diagnostico.append({
        "componente": "Python Runtime",
        "estado": "OK" if py_ok else "ERROR",
        "requerido": True,
        "detalle": f"Python {sys.version.split()[0]}",
    })

    gcc_path = shutil.which("gcc")
    diagnostico.append({
        "componente": "Compilador GCC",
        "estado": "OK" if gcc_path else "ERROR",
        "requerido": True,
        "detalle": gcc_path or "No encontrado (requerido para compilar y generar código objeto)",
    })

    objdump_path = shutil.which("objdump")
    diagnostico.append({
        "componente": "Desensamblador objdump",
        "estado": "OK" if objdump_path else "ERROR",
        "requerido": True,
        "detalle": objdump_path or "No encontrado (requerido para desensamblado de código)",
    })

    todo_ok = py_ok and bool(gcc_path) and bool(objdump_path)

    if json_output:
        payload = {
            "schema_version": "1.0.0",
            "herramienta": "rachel",
            "ok": todo_ok,
            "componentes": diagnostico,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        raise typer.Exit(code=0 if todo_ok else 1)

    tabla = Table(title="🏥 Diagnóstico del Entorno RACHEL (doctor)", border_style="cyan")
    tabla.add_column("Componente", style="bold white")
    tabla.add_column("Estado", justify="center")
    tabla.add_column("Detalle")

    for c in diagnostico:
        color = "bold green" if c["estado"] == "OK" else "bold red"
        simbolo = "✓" if c["estado"] == "OK" else "✗"
        tabla.add_row(str(c["componente"]), f"[{color}]{simbolo} {c['estado']}[/{color}]", str(c["detalle"]))

    console.print(tabla)
    if not todo_ok:
        console.print("\n[bold red]Instalá gcc y binutils (`sudo apt install gcc binutils` o equivalente).[/bold red]")
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
