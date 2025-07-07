import os
import shutil
import time
import json
import typer
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

# Paths
CONFIG_PATH = os.path.join("storage", "config.json")
BACKUPS_DIR = "backups"
VERSIONS_DIR = "versions"
DEBUG_FOLDER = "steamdb_debug"

# Color scheme
app = typer.Typer()
console = Console(theme=Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "error": "bold red",
    "success": "bold green",
    "title": "bold blue",
    "highlight": "bold yellow",
    "debug": "dim grey50"
}))

os.makedirs("storage", exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)
os.makedirs(DEBUG_FOLDER, exist_ok=True)

DEBUG_MODE = False

# === Utility Functions ===

def debug_log(msg: str):
    if DEBUG_MODE:
        console.print(f"[debug]{msg}[/debug]")
        with open(os.path.join(DEBUG_FOLDER, "debug_log.txt"), "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


def load_config():
    return json.load(open(CONFIG_PATH)) if os.path.exists(CONFIG_PATH) else {}


def save_config(config: dict):
    json.dump(config, open(CONFIG_PATH, "w"), indent=4)


def confirm_action(warning: str):
    console.print(f"[warning]{warning}[/warning]")
    return Prompt.ask("Are you sure you want to continue? (yes/no)", choices=["yes", "no"]) == "yes"


def list_directory(path: str):
    return sorted([item for item in os.listdir(path) if os.path.isdir(os.path.join(path, item))])


def count_files(path: str):
    total = 0
    for _, _, files in os.walk(path):
        total += len(files)
    return total


def copy_with_progress(src, dst, action="Copying"):
    total_files = count_files(src)
    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"{action}...", total=total_files)

        for foldername, subfolders, filenames in os.walk(src):
            relative_path = os.path.relpath(foldername, src)
            target_folder = os.path.join(dst, relative_path)
            os.makedirs(target_folder, exist_ok=True)

            for filename in filenames:
                src_file = os.path.join(foldername, filename)
                dst_file = os.path.join(target_folder, filename)
                shutil.copy2(src_file, dst_file)
                progress.update(task, advance=1)


# === Main Functions ===

def show_menu():
    clear_terminal()
    console.print(Panel.fit("[title]Worldbox Rewind Manager[/title]", border_style="blue"))
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="dim", width=12)
    table.add_column("Description")
    table.add_row("1", "Set Installation Path")
    table.add_row("2", "Backup Current Installation")
    table.add_row("3", "List Backups and Versions")
    table.add_row("4", "Restore Backup")
    table.add_row("5", "Downgrade to Version")
    table.add_row("6", "Exit")
    console.print(table)


def set_path():
    path = Prompt.ask("Enter installation path")
    if not os.path.exists(path):
        console.print(f"[error]Invalid path: {path}[/error]")
        input("\nPress Enter to continue...")

        return
    config = load_config()
    config["installation_path"] = path
    save_config(config)
    console.print(f"[success]Path saved: {path}[/success]")


def backup():
    config = load_config()
    path = config.get("installation_path")
    if not path or not os.path.exists(path):
        console.print("[error]Invalid or missing installation path.[/error]")
        return

    if not confirm_action("This will create a full backup of your installation."):
        return

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = os.path.join(BACKUPS_DIR, f"backup-{timestamp}")


    try:
        copy_with_progress(path, backup_path, action="Backing up")
        console.print(f"[success]Backup created at: {backup_path}[/success]")
        input("\nPress Enter to continue...")
    except Exception as e:
        console.print(f"[error]Backup failed: {e}[/error]")
        input("\nPress Enter to continue...")



def list_versions():
    clear_terminal()
    console.print(Panel.fit("[title]Available Backups and Versions[/title]", border_style="blue"))

    # Backups
    backups = list_directory(BACKUPS_DIR)
    console.print("\n[bold underline]Backups:[/bold underline]")
    if backups:
        for b in backups:
            console.print(f"• {b}")
    else:
        console.print("[info]No backups found.[/info]")

    # Versions
    console.print("\n[bold underline]Versions:[/bold underline]")
    if not os.path.exists(VERSIONS_DIR):
        console.print("[warning]Versions directory not found.[/warning]")
    else:
        for platform in list_directory(VERSIONS_DIR):
            console.print(f"[highlight]{platform}[/highlight]")
            versions = list_directory(os.path.join(VERSIONS_DIR, platform))
            if versions:
                for v in versions:
                    console.print(f"  • {v}")
            else:
                console.print("  [info]No versions found.[/info]")
    input("\nPress Enter to continue...")



   


def restore_backup():
    config = load_config()
    path = config.get("installation_path")
    if not path or not os.path.exists(path):
        console.print("[error]Invalid or missing installation path.[/error]")
        input("\nPress Enter to continue...")

        return

    backups = list_directory(BACKUPS_DIR)
    if not backups:
        console.print("[info]No backups available.[/info]")
        return

    console.print("Choose a backup:")
    for i, b in enumerate(backups, start=1):
        console.print(f"{i}. {b}")
    choice = IntPrompt.ask("Enter number", choices=[str(i) for i in range(1, len(backups)+1)])
    selected = backups[choice - 1]

    if not confirm_action("This will completely overwrite your current installation!"):
        return

    backup_path = os.path.join(BACKUPS_DIR, selected)

    try:
        shutil.rmtree(path)
        copy_with_progress(backup_path, path, action="Restoring backup")
        console.print(f"[success]Restored backup: {selected}[/success]")
        input("\nPress Enter to continue...")
    except Exception as e:
        console.print(f"[error]Restore failed: {e}[/error]")
        input("\nPress Enter to continue...")



def downgrade_version():
    config = load_config()
    path = config.get("installation_path")
    if not path or not os.path.exists(path):
        console.print("[error]Invalid or missing installation path.[/error]")
        input("\nPress Enter to continue...")
        return

    platforms = list_directory(VERSIONS_DIR)
    if not platforms:
        console.print("[info]No platforms available.[/info]")
        input("\nPress Enter to continue...")
        return

    console.print("Choose a platform:")
    for i, p in enumerate(platforms, start=1):
        console.print(f"{i}. {p}")
    plat_choice = IntPrompt.ask("Enter number", choices=[str(i) for i in range(1, len(platforms)+1)])
    platform = platforms[plat_choice - 1]

    versions = list_directory(os.path.join(VERSIONS_DIR, platform))
    if not versions:
        console.print("[info]No versions for this platform.[/info]")
        input("\nPress Enter to continue...")
        return

    console.print("Choose version:")
    for i, v in enumerate(versions, start=1):
        console.print(f"{i}. {v}")
    ver_choice = IntPrompt.ask("Enter number", choices=[str(i) for i in range(1, len(versions)+1)])
    version = versions[ver_choice - 1]

    if not confirm_action(f"This will overwrite your current installation with version '{version}'!"):
        return

    source = os.path.join(VERSIONS_DIR, platform, version)

    try:
        shutil.rmtree(path)
        copy_with_progress(source, path, action="Downgrading")
        console.print(f"[success]Downgraded to {version} on {platform}[/success]")
        input("\nPress Enter to continue...")
    except Exception as e:
        console.print(f"[error]Downgrade failed: {e}[/error]")
        input("\nPress Enter to continue...")



# === Entry Point ===

@app.command()
def main(debug: bool = typer.Option(False, help="Enable debug logging")):
    global DEBUG_MODE
    DEBUG_MODE = debug
    debug_log("Application started")

    while True:
        show_menu()
        choice = IntPrompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6"])
        match choice:
            case 1: set_path()
            case 2: backup()
            case 3: list_versions()
            case 4: restore_backup()
            case 5: downgrade_version()
            case 6:
                console.print("[info]Goodbye![/info]")
                break

    debug_log("Application exited")


if __name__ == "__main__":
    app()
