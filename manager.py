import os
import shutil
import time
import json
import typer  # type: ignore
from rich.console import Console  # type: ignore
from rich.prompt import Prompt, IntPrompt  # type: ignore
from rich.panel import Panel  # type: ignore
from rich.table import Table  # type: ignore
from rich.theme import Theme  # type: ignore

CONFIG_PATH = os.path.join("storage", "config.json")
BACKUPS_DIR = "backups"
DEBUG_MODE = False
DEBUG_FOLDER = "steamdb_debug"

os.makedirs(DEBUG_FOLDER, exist_ok=True)
os.makedirs("storage", exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "error": "bold red",
    "success": "bold green",
    "title": "bold blue",
    "highlight": "bold yellow",
    "debug": "dim grey50"
})

app = typer.Typer()
console = Console(theme=custom_theme)

def debug_log(message: str, save_to_file: bool = True):
    if DEBUG_MODE:
        console.print(f"[debug]{message}[/debug]")
        if save_to_file:
            with open(os.path.join(DEBUG_FOLDER, "debug_log.txt"), "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

def save_config(config: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")

def show_menu():
    
    console.print(Panel.fit("[title]Worldbox Rewind Manager[/title]", border_style="blue"))
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="dim", width=12)
    table.add_column("Description", width=40)
    table.add_row("1", "Set Installation Path")
    table.add_row("2", "Backup Current Installation")
    table.add_row("3", "List Versions")
    table.add_row("4", "Restore Backup")
    table.add_row("5", "Downgrade to Version")
    table.add_row("6", "Exit")
    console.print(table)

def set_path():
    installation_path = Prompt.ask("Enter your installation path")
    if not os.path.exists(installation_path):
        console.print(f"[error]Path does not exist: {installation_path}[/error]")
        return
    config = load_config()
    config["installation_path"] = installation_path
    save_config(config)
    console.print(f"[success]Installation path saved: {installation_path}[/success]")

def backup():
    config = load_config()
    installation_path = config.get("installation_path")
    if not installation_path:
        console.print("[error]Installation path not set. Please set it first.[/error]")
        return
    if not os.path.exists(installation_path):
        console.print(f"[error]Installation path does not exist: {installation_path}[/error]")
        return

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = os.path.join(BACKUPS_DIR, f"backup-{timestamp}")

    try:
        shutil.move(installation_path, backup_path)
        console.print(f"[success]Backup created at: {backup_path}[/success]")
        os.makedirs(installation_path, exist_ok=True)
    except Exception as e:
        console.print(f"[error]Failed to backup installation: {e}[/error]")

@app.command()
def main():
    debug_log("Manager script started")
    while True:
        show_menu()
        choice = IntPrompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6"])
        if choice == 1:
            set_path()
        elif choice == 2:
            backup()
        elif choice == 3:
            list_versions()
        elif choice == 4:
            restore_backup()
        elif choice == 5:
            downgrade_version()
        elif choice == 6:
            console.print("[info]Exiting...[/info]")
            break
        else:
            console.print("[error]Invalid choice[/error]")
    debug_log("Manager script finished")

def list_versions():
    clear_terminal()
    console.print(Panel.fit("[title]Available Backups and Versions[/title]", border_style="blue"))

    
    console.print("[bold underline]Backups:[/bold underline]")
    if not os.path.exists(BACKUPS_DIR):
        console.print("[warning]No backups directory found.[/warning]")
    else:
        backups = sorted(os.listdir(BACKUPS_DIR))
        if not backups:
            console.print("[info]No backups found.[/info]")
        else:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Backup Name", style="dim")
            for backup in backups:
                table.add_row(backup)
            console.print(table)

    
    VERSIONS_DIR = "versions"
    console.print("\n[bold underline]Versions:[/bold underline]")
    if not os.path.exists(VERSIONS_DIR):
        console.print("[warning]No versions directory found.[/warning]")
    else:
        platforms = sorted(os.listdir(VERSIONS_DIR))
        if not platforms:
            console.print("[info]No versions found.[/info]")
        else:
            for platform in platforms:
                platform_path = os.path.join(VERSIONS_DIR, platform)
                if os.path.isdir(platform_path):
                    versions = sorted(os.listdir(platform_path))
                    console.print(f"\n[highlight]{platform}[/highlight]")
                    if not versions:
                        console.print("  [info]No versions found for this platform.[/info]")
                    else:
                        table = Table(show_header=True, header_style="bold magenta")
                        table.add_column("Version", style="dim")
                        for version in versions:
                            table.add_row(version)
                        console.print(table)

    Prompt.ask("Press Enter to return to menu")

def restore_backup():
    clear_terminal()
    console.print(Panel.fit("[title]Restore Backup[/title]", border_style="blue"))

    config = load_config()
    installation_path = config.get("installation_path")
    if not installation_path:
        console.print("[error]Installation path not set. Please set it first.[/error]")
        return
    if not os.path.exists(installation_path):
        console.print(f"[error]Installation path does not exist: {installation_path}[/error]")
        return

    if not os.path.exists(BACKUPS_DIR):
        console.print("[error]Backups directory not found.[/error]")
        return

    backups = sorted([d for d in os.listdir(BACKUPS_DIR) if os.path.isdir(os.path.join(BACKUPS_DIR, d))])
    if not backups:
        console.print("[info]No backups found.[/info]")
        return

    console.print("Select backup to restore:")
    for i, backup in enumerate(backups, start=1):
        console.print(f"{i}. {backup}")
    backup_choice = IntPrompt.ask("Enter number", choices=[str(i) for i in range(1, len(backups)+1)])
    selected_backup = backups[backup_choice - 1]

    console.print("[warning]WARNING: You should backup your current installation before restoring![/warning]")
    confirm = Prompt.ask("Are you sure you want to restore this backup? (yes/no)", choices=["yes", "no"])
    if confirm != "yes":
        console.print("[info]Restore cancelled.[/info]")
        return

    source_path = os.path.join(BACKUPS_DIR, selected_backup)
    if not os.path.exists(source_path):
        console.print(f"[error]Selected backup path does not exist: {source_path}[/error]")
        return

    try:
        from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn # type: ignore

        
        console.clear()
        console.print("[info]Removing current installation files...[/info]")
        for item in os.listdir(installation_path):
            item_path = os.path.join(installation_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

        
        console.print("[info]Restoring backup files...[/info]")
        items = os.listdir(source_path)
        with Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Restoring files", total=len(items))
            for item in items:
                s = os.path.join(source_path, item)
                d = os.path.join(installation_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
                progress.update(task, advance=1)

        console.print(f"[success]Restored backup {selected_backup} to installation path.[/success]")
    except Exception as e:
        console.print(f"[error]Failed to restore backup: {e}[/error]")

def downgrade_version():
    clear_terminal()
    console.print(Panel.fit("[title]Downgrade to Version[/title]", border_style="blue"))

    config = load_config()
    installation_path = config.get("installation_path")
    if not installation_path:
        console.print("[error]Installation path not set. Please set it first.[/error]")
        return
    if not os.path.exists(installation_path):
        console.print(f"[error]Installation path does not exist: {installation_path}[/error]")
        return

    VERSIONS_DIR = "versions"
    if not os.path.exists(VERSIONS_DIR):
        console.print("[error]Versions directory not found.[/error]")
        return

    platforms = sorted([d for d in os.listdir(VERSIONS_DIR) if os.path.isdir(os.path.join(VERSIONS_DIR, d))])
    if not platforms:
        console.print("[info]No platforms found in versions directory.[/info]")
        return

    console.print("Select platform:")
    for i, platform in enumerate(platforms, start=1):
        console.print(f"{i}. {platform}")
    platform_choice = IntPrompt.ask("Enter number", choices=[str(i) for i in range(1, len(platforms)+1)])
    selected_platform = platforms[platform_choice - 1]

    platform_path = os.path.join(VERSIONS_DIR, selected_platform)
    versions = sorted([d for d in os.listdir(platform_path) if os.path.isdir(os.path.join(platform_path, d))])
    if not versions:
        console.print(f"[info]No versions found for platform {selected_platform}.[/info]")
        return

    console.print(f"Select version to downgrade to for platform [highlight]{selected_platform}[/highlight]:")
    for i, version in enumerate(versions, start=1):
        console.print(f"{i}. {version}")
    version_choice = IntPrompt.ask("Enter number", choices=[str(i) for i in range(1, len(versions)+1)])
    selected_version = versions[version_choice - 1]

    console.print("[warning]WARNING: You should backup your current installation before downgrading![/warning]")
    confirm = Prompt.ask("Are you sure you want to downgrade? (yes/no)", choices=["yes", "no"])
    if confirm != "yes":
        console.print("[info]Downgrade cancelled.[/info]")
        return

    source_path = os.path.join(platform_path, selected_version)
    if not os.path.exists(source_path):
        console.print(f"[error]Selected version path does not exist: {source_path}[/error]")
        return

    try:
        from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn # type: ignore

        
        console.clear()
        console.print("[info]Removing current installation files...[/info]")
        for item in os.listdir(installation_path):
            item_path = os.path.join(installation_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

        
        console.print("[info]Copying selected version files...[/info]")
        items = os.listdir(source_path)
        with Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Copying files", total=len(items))
            for item in items:
                s = os.path.join(source_path, item)
                d = os.path.join(installation_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
                progress.update(task, advance=1)

        console.print(f"[success]Downgraded to version {selected_version} for platform {selected_platform}.[/success]")
    except Exception as e:
        console.print(f"[error]Failed to downgrade: {e}[/error]")

if __name__ == "__main__":
    app()
