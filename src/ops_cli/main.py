from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ops_cli.models import BackupConfig, CleanConfig, DeployConfig, GenerateConfig

# Typer cria a aplicacao CLI e usa as assinaturas das funcoes para montar o help.
app = typer.Typer(
    help="Small operations CLI example with Typer, Rich and Pydantic.",
    no_args_is_help=True,
)
console = Console()


def fail_validation(error: ValidationError) -> None:
    # Rich deixa os erros de validacao em uma tabela facil de escanear.
    table = Table(title="Validation failed", show_header=True, header_style="bold red")
    table.add_column("Field")
    table.add_column("Problem")

    for item in error.errors():
        field = ".".join(str(part) for part in item["loc"])
        # escape evita que regex com [] seja interpretada como markup do Rich.
        table.add_row(escape(field), escape(item["msg"]))

    console.print(table)
    raise typer.Exit(code=1)


def print_config(title: str, values: dict[str, object]) -> None:
    # Helper pequeno para todos os comandos mostrarem a config do mesmo jeito.
    table = Table(title=title, show_header=False)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")

    for key, value in values.items():
        table.add_row(key, str(value))

    console.print(table)


@app.command()
def backup(
    source: Path = typer.Argument(..., help="Folder or file to back up."),
    destination: Path = typer.Option(Path("backups"), "--destination", "-d", help="Backup output folder."),
    compress: bool = typer.Option(True, "--compress/--no-compress", help="Create a compressed backup."),
) -> None:
    """Prepare a backup job."""
    try:
        # A config concentra as regras; o comando fica responsavel pelo fluxo.
        config = BackupConfig(source=source, destination=destination, compress=compress)
    except ValidationError as error:
        fail_validation(error)

    config.destination.mkdir(parents=True, exist_ok=True)

    print_config("Backup job", config.model_dump())
    # Progress aqui e demonstrativo; em um backup real cada task faria trabalho.
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task("Collecting files...", total=None)
        progress.add_task("Writing manifest...", total=None)

    mode = "compressed" if config.compress else "plain"
    console.print(Panel.fit(f"Backup ready in [bold]{config.destination}[/bold] ({mode})", border_style="green"))


@app.command()
def deploy(
    artifact: Path = typer.Argument(..., help="Build artifact or folder to deploy."),
    environment: str = typer.Option("dev", "--environment", "-e", help="dev, staging or prod."),
    version: str = typer.Option("0.1.0", "--version", "-v", help="Semantic version like 1.2.3."),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
) -> None:
    """Validate and simulate a deploy."""
    try:
        config = DeployConfig(artifact=artifact, environment=environment, version=version)
    except ValidationError as error:
        fail_validation(error)

    print_config("Deploy plan", config.model_dump())

    # Exemplo de protecao simples para ambientes sensiveis.
    if config.environment == "prod" and not confirm:
        confirmed = typer.confirm("Deploy to production?")
        if not confirmed:
            console.print("[yellow]Deploy cancelled.[/yellow]")
            raise typer.Exit(code=0)

    console.print(Panel.fit(f"Deployed version [bold]{config.version}[/bold] to {config.environment}", border_style="green"))


@app.command()
def clean(
    target: Path = typer.Argument(..., help="Folder to clean."),
    older_than_days: int = typer.Option(7, "--older-than", "-o", help="Only clean files older than this many days."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen without deleting anything."),
) -> None:
    """Validate and simulate cleaning old files."""
    try:
        config = CleanConfig(target=target, older_than_days=older_than_days, dry_run=dry_run)
    except ValidationError as error:
        fail_validation(error)

    print_config("Clean job", config.model_dump())
    action = "Would clean" if config.dry_run else "Cleaned"
    console.print(Panel.fit(f"{action} files older than {config.older_than_days} days in {config.target}", border_style="blue"))


@app.command()
def generate(
    name: str = typer.Option(..., "--name", "-n", help="Project name to generate."),
    environment: str = typer.Option("dev", "--environment", "-e", help="dev, staging or prod."),
    output: Path = typer.Option(Path("generated"), "--output", "-o", help="Output folder."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace an existing file."),
) -> None:
    """Generate a tiny config file."""
    try:
        config = GenerateConfig(name=name, environment=environment, output=output)
    except ValidationError as error:
        fail_validation(error)

    config.output.mkdir(parents=True, exist_ok=True)
    config_file = config.output / f"{config.name}.toml"

    # Evita sobrescrever arquivo sem o usuario pedir explicitamente.
    if config_file.exists() and not overwrite:
        console.print(f"[red]File already exists:[/red] {config_file}")
        raise typer.Exit(code=1)

    config_file.write_text(
        f'name = "{config.name}"\n'
        f'environment = "{config.environment}"\n'
        'debug = true\n',
        encoding="utf-8",
    )

    print_config("Generated config", {"file": config_file, "environment": config.environment})
    console.print(Panel.fit("Generation complete", border_style="green"))


if __name__ == "__main__":
    app()
