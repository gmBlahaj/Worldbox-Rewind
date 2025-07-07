import os
import subprocess
import time
from typing import Optional
import typer
from rich import print
from rich.prompt import Prompt, IntPrompt
from rich.panel import Panel
from rich.console import Console
from rich.table import Table
from rich.theme import Theme
import shutil
import re
import json
import getpass

# === Paths etc ===
DEBUG_MODE = True
DEBUG_FOLDER = "steamdb_debug"
VERSIONS_DIR = "versions"
CONFIG_PATH = os.path.join("storage", "config.json")

# === Platform Definitions ===
PLATFORM_DEPOTS = {
    "Windows": "1206561",
    "Linux": "1206562",
    "Mac": "1206563"
}
DEPOT_PLATFORMS = {v: k for k, v in PLATFORM_DEPOTS.items()}
APP_ID = "1206560"

# === Folder Initialization ===
os.makedirs(DEBUG_FOLDER, exist_ok=True)
os.makedirs("storage", exist_ok=True)
for folder in PLATFORM_DEPOTS.keys():
    os.makedirs(os.path.join(VERSIONS_DIR, folder), exist_ok=True)

# === Theme Setup ===
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

# === App Init ===
app = typer.Typer()
console = Console(theme=custom_theme)


# === Debug Logging ===
def debug_log(message: str, save_to_file: bool = True):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"{timestamp} - {message}"
    if DEBUG_MODE:
        console.print(f"[debug]{full_msg}[/debug]")
        if save_to_file:
            with open(os.path.join(DEBUG_FOLDER, f"debug_log_{time.strftime('%Y%m%d')}.txt"), "a", encoding="utf-8") as f:
                f.write(full_msg + "\n")


# === Config Management ===
def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def get_username() -> str:
    config = load_config()
    if "username" in config:
        return config["username"]
    username = Prompt.ask("Steam username")
    config["username"] = username
    save_config(config)
    return username


# === SteamCMD Check ===
def check_steamcmd() -> bool:
    return shutil.which("steamcmd") is not None


# === Platform Menu ===
def show_platform_menu() -> str:
    debug_log("Showing platform selection menu")
    console.print(Panel.fit("[title]Select Platform Version:[/title]", border_style="blue"))
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="dim", width=12)
    table.add_column("Platform", width=12)
    table.add_column("Depot ID", style="highlight")
    for i, (platform, depot_id) in enumerate(PLATFORM_DEPOTS.items(), start=1):
        table.add_row(str(i), platform, depot_id)
        debug_log(f"Platform option {i}: {platform} (Depot: {depot_id})")
    console.print(table)
    while True:
        choice = IntPrompt.ask("Select platform (1-3)", choices=["1", "2", "3"], show_choices=False)
        if 1 <= choice <= len(PLATFORM_DEPOTS):
            selected = list(PLATFORM_DEPOTS.keys())[choice - 1]
            debug_log(f"User selected: {selected} (Depot: {PLATFORM_DEPOTS[selected]})")
            return PLATFORM_DEPOTS[selected]


# === Tutorial Display ===
def show_tutorial():
    tutorial = """
[title]How to find a Manifest ID[/title]

1. Visit SteamDB WorldBox depot for your platform:
   - [bold]Windows:[/bold] https://steamdb.info/depot/1206561/manifests/
   - [bold]Linux:[/bold] https://steamdb.info/depot/1206562/manifests
   - [bold]Mac:[/bold] https://steamdb.info/depot/1206563/manifests

2. Copy the Manifest ID you want from the list.
"""
    console.print(Panel(tutorial, border_style="blue", title="Tutorial"))


def show_tutorial_if_needed(skip: bool):
    if not skip:
        show_tutorial()


# === Output Filter ===
def enableoutput(line: str) -> bool:
    skip_patterns = [
        r"\[\s*\d%\]", r"\(\d.*(?:von|of).*\)",
        r"Redirecting stderr to", r"Logging directory:",
        r"UpdateUI: skip show logo", r"^\s*$",
        r"KeyValues Error", r"src/tier1/KeyValues.cpp"
    ]
    return not any(re.search(pattern, line) for pattern in skip_patterns)


# === Safe Move Files ===
def safe_move(src_dir: str, dest_dir: str):
    for item in os.listdir(src_dir):
        s, d = os.path.join(src_dir, item), os.path.join(dest_dir, item)
        if os.path.exists(d):
            if os.path.isdir(d):
                shutil.rmtree(d)
            else:
                os.remove(d)
        shutil.move(s, d)


# === Abort Helper ===
def abort(message: str = "Aborted."):
    console.print(f"[warning]{message}[/warning]")
    raise typer.Exit(1)


# === SteamCMD Execution ===
def steamcmd(username: str, password: Optional[str], manifest_id: str, depot_id: str):
    debug_log(f"Preparing SteamCMD for manifest {manifest_id} (depot {depot_id})")
    platform_folder = DEPOT_PLATFORMS.get(depot_id, "Unknown")
    version_path = os.path.join(VERSIONS_DIR, platform_folder, manifest_id)
    os.makedirs(version_path, exist_ok=True)

    command = ["utils/steamcmd.exe", "+login", username]
    if password:
        command.append(password)
    command.extend([
        "+download_depot", APP_ID, depot_id, manifest_id,
        "+quit"
    ])
    debug_log(f"Executing: {' '.join(command)}")
    console.print("[info]Running SteamCMD...[/info]")

    depot_download_path = None

    console.print(Panel.fit(
        "[bold yellow]If Steam Guard is enabled, approve the login on your Steam Mobile App or email.[/bold yellow]\n\n"
        "This process may take a few minutes. Output will be shown below:",
        border_style="cyan"
    ))

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    while True:
        if process.stdout is None:
            break
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            line = output.strip()
            if "Steam Guard code" in line or "Steam Guard" in line:
                steamguard_code = Prompt.ask("Enter Steam Guard code (Just press enter if approved In-App)")
                if process.stdin:
                    process.stdin.write(steamguard_code + "\n")
                    process.stdin.flush()
            elif "Depot download complete" in line:
                match = re.search(r'Depot download complete : "([^"]+)"', line)
                if match:
                    depot_download_path = re.sub(r'\\', '/', match.group(1))
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
            safe_move(depot_download_path, version_path)
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


# === CLI Entry Point ===
@app.command()
def main(no_tutorial: bool = typer.Option(False, "--no-tutorial", help="Skip manifest tutorial.")):
    debug_log("Script started")
    console.print(Panel.fit("[success]WorldBox Rewind[/success]", border_style="green"))

    if not check_steamcmd():
        console.print("[error]steamcmd not found in PATH. Please install it first.[/error]")
        raise typer.Exit(1)

    try:
        username = get_username()
        password = getpass.getpass("Steam password: ").strip() or None

        depot_id = show_platform_menu()
        show_tutorial_if_needed(no_tutorial)
        manifest_id = Prompt.ask("[bold yellow]Enter Manifest ID[/bold yellow]").strip()

        platform_folder = DEPOT_PLATFORMS.get(depot_id, "Unknown")
        version_path = os.path.join(VERSIONS_DIR, platform_folder, manifest_id)

        if os.path.exists(version_path) and os.listdir(version_path):
            overwrite = Prompt.ask(
                f"[warning]Version {manifest_id} already exists. Redownload?[/warning] (y/n)",
                choices=["y", "n"], default="n"
            )
            if overwrite.lower() != "y":
                abort("Skipped existing version.")

        steamcmd(username, password, manifest_id, depot_id)
    except KeyboardInterrupt:
        abort("Interrupted by user.")
    except Exception as e:
        debug_log(f"Unhandled exception: {e}")
        console.print(f"[error]Unexpected error: {e}[/error]")
        raise typer.Exit(1)
    finally:
        debug_log("Script finished")


if __name__ == "__main__":
    app()
