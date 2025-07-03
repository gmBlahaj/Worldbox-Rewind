import os
import subprocess
import time
from typing import Optional
import typer # type: ignore
from rich import print # type: ignore
from rich.prompt import Prompt, IntPrompt # type: ignore
from rich.panel import Panel # type: ignore
from rich.console import Console # type: ignore
from rich.table import Table # type: ignore
from rich.theme import Theme # type: ignore
import shutil
import re
import json

DEBUG_MODE = False
DEBUG_FOLDER = "steamdb_debug"
VERSIONS_DIR = "versions"
CONFIG_PATH = os.path.join("storage", "config.json")

os.makedirs(DEBUG_FOLDER, exist_ok=True)
os.makedirs("storage", exist_ok=True)
for folder in ["Windows", "Linux", "Mac"]:
    os.makedirs(os.path.join(VERSIONS_DIR, folder), exist_ok=True)

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "error": "bold red",
    "success": "bold green",
    "title": "bold blue",
    "highlight": "bold yellow",
    "steamcmd": "dim white",
    "steamcmd_error": "bold red",
    "steamcmd_warning": "bold yellow",
    "steamcmd_success": "bold green",
    "debug": "dim grey50"
})

app = typer.Typer()
console = Console(theme=custom_theme)

DEPOTS = {
    "Windows": "1206561",
    "Linux": "1206562",
    "Mac": "1206563"
}

APP_ID = "1206560"


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
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def get_username() -> str:
    config = load_config()
    if "username" in config:
        return config["username"]
    username = Prompt.ask("Steam username")
    config["username"] = username
    save_config(config)
    return username

def show_platform_menu() -> str:
    debug_log("Showing platform selection menu")
    console.print(Panel.fit("[title]Select Platform Version:[/title]", border_style="blue"))
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="dim", width=12)
    table.add_column("Platform", width=12)
    table.add_column("Depot ID", style="highlight")
    for i, (platform, depot_id) in enumerate(DEPOTS.items(), start=1):
        table.add_row(str(i), platform, depot_id)
        debug_log(f"Platform option {i}: {platform} (Depot: {depot_id})")
    console.print(table)
    while True:
        choice = IntPrompt.ask("Select platform (1-3)", choices=["1", "2", "3"], show_choices=False)
        if 1 <= choice <= len(DEPOTS):
            selected = list(DEPOTS.keys())[choice - 1]
            debug_log(f"User selected: {selected} (Depot: {DEPOTS[selected]})")
            return DEPOTS[selected]

def show_tutorial():
    tutorial = """
[title]How to find a Manifest ID[/title]

1. Visit SteamDB WorldBox depot for your platform:
   - [bold]Windows:[/bold] [link=https://steamdb.info/depot/1206561/manifests/]Link[/link]
   - [bold]Linux:[/bold] [link=https://steamdb.info/depot/1206562/manifests/]Link[/link]
   - [bold]Mac:[/bold] [link=https://steamdb.info/depot/1206563/manifests/]Link[/link]

2. Copy the Manifest ID you want from the list.
"""
    console.print(Panel(tutorial, border_style="blue", title="Tutorial"))

def enableoutput(line: str) -> bool:
    skip_patterns = [
        r"\[\s*\d+%\]", r"\(\d+.*(?:von|of).*\)",
        r"Redirecting stderr to", r"Logging directory:",
        r"UpdateUI: skip show logo", r"^\s*$",
        r"KeyValues Error", r"src/tier1/KeyValues.cpp"
    ]
    return not any(re.search(pattern, line) for pattern in skip_patterns)

import subprocess

def steamcmd(username: str, password: Optional[str], manifest_id: str, depot_id: str):
    debug_log(f"Preparing SteamCMD for manifest {manifest_id} (depot {depot_id})")
    platform_folder = {"1206561": "Windows", "1206562": "Linux", "1206563": "Mac"}.get(depot_id, "Unknown")
    version_path = os.path.join(VERSIONS_DIR, platform_folder, manifest_id)
    os.makedirs(version_path, exist_ok=True)

    command = ["steamcmd", "+login", username]
    if password:
        command.append(password)
    command.extend([
        "+download_depot", APP_ID, depot_id, manifest_id,
        "+quit"
    ])
    debug_log(f"Executing: {' '.join(command)}")
    console.print(f"[info]Running SteamCMD for manifest {manifest_id}...[/info]")

    depot_download_path = None

    console.print(Panel.fit(
        "[bold yellow]If Steam Guard is enabled, approve the login on your Steam Mobile App or email.[/bold yellow]\n\n"
        "This process may take a few minutes. Output will be shown below:",
        border_style="cyan"
    ))

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)

    while True:
        if process.stdout is None:
            break
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            line = output.strip()
            if "Steam Guard code" in line or "Steam Guard" in line:
                steamguard_code = Prompt.ask("Enter Steam Guard code")
                if process.stdin:
                    process.stdin.write(steamguard_code + "\n")
                    process.stdin.flush()
            elif "Depot download complete" in line:
                match = re.search(r'Depot download complete : "([^"]+)"', line)
                if match:
                    depot_download_path = re.sub(r'\\+', '/', match.group(1))
                    debug_log(f"Download path: {depot_download_path}")
            elif enableoutput(line):
                console.print(f"[steamcmd]{line}[/steamcmd]")

    return_code = process.poll()
    debug_log(f"SteamCMD exited with code {return_code}")

    if return_code != 0:
        console.print("[error]SteamCMD failed.[/error]")
        raise typer.Exit(1)

    if depot_download_path and os.path.exists(depot_download_path):
        debug_log(f"Moving files to {version_path}")
        try:
            for item in os.listdir(depot_download_path):
                shutil.move(os.path.join(depot_download_path, item), os.path.join(version_path, item))
            console.print(f"[success]Saved version to: {version_path}[/success]")
            try:
                shutil.rmtree(os.path.dirname(depot_download_path))
                debug_log(f"Cleaned up: {os.path.dirname(depot_download_path)}")
            except Exception as e:
                debug_log(f"Cleanup failed: {e}")
        except Exception as e:
            console.print(f"[error]Failed to move files: {e}[/error]")
            debug_log(f"Move error: {e}")
    else:
        console.print(f"[error]Download path not found: {depot_download_path}[/error]")


@app.command()
def main():
    debug_log("Script started")
    console.print(Panel.fit("[success]WorldBox Rewind Bulk Downloader[/success]", border_style="green"))

    try:
        username = get_username()
        password = Prompt.ask("Steam password:", password=True)
        password = password if password else None

        depot_id = show_platform_menu()
        show_tutorial()

        bulk_file = Prompt.ask("Enter path to txt file with list of Manifest IDs (leave empty to download single)")
        if bulk_file and os.path.exists(bulk_file):
            with open(bulk_file, "r") as f:
                manifest_ids = [line.strip() for line in f if line.strip()]
            for manifest_id in manifest_ids:
                console.print(f"[info]Downloading manifest ID: {manifest_id}[/info]")
                steamcmd(username, password, manifest_id, depot_id)
        else:
            manifest_id = Prompt.ask("[bold yellow]Enter Manifest ID[/bold yellow]")
            steamcmd(username, password, manifest_id, depot_id)
    except Exception as e:
        debug_log(f"Error: {e}")
        console.print(f"[error]Error: {e}[/error]")
        raise typer.Exit(1)
    finally:
        debug_log("Script finished")


if __name__ == "__main__":
    app()
