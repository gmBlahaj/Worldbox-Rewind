import os
import subprocess
import time
from typing import Optional
import typer
from rich import print
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.panel import Panel
from rich.console import Console
from rich.table import Table
from rich.theme import Theme
import shutil
import re
import json
import getpass
import threading
import requests


DEBUG_MODE = True
DEBUG_FOLDER = "steamdb_debug"
VERSIONS_DIR = "versions"
CONFIG_PATH = os.path.join("storage", "config.json")
MANIFESTS_URL = "https://example.com/manifests.json" 
MANIFESTS_CACHE = os.path.join("storage", "manifests_cache.json")

PLATFORM_DEPOTS = {
    "Windows": "1206561",
    "Linux": "1206562",
    "Mac": "1206563"
}
DEPOT_PLATFORMS = {v: k for k, v in PLATFORM_DEPOTS.items()}
APP_ID = "1206560"

os.makedirs(DEBUG_FOLDER, exist_ok=True)
os.makedirs("storage", exist_ok=True)
for folder in PLATFORM_DEPOTS.keys():
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


def get_manifest_data() -> dict:
    """Fetch manifest data from URL or cache"""
    try:
        
        if os.path.exists(MANIFESTS_CACHE):
            with open(MANIFESTS_CACHE, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                if cached_data:
                    debug_log("Loaded manifests from cache")
                    return cached_data
        
        
        debug_log("Fetching manifests from remote URL")
        response = requests.get(MANIFESTS_URL)
        response.raise_for_status()
        data = response.json()
        
        
        with open(MANIFESTS_CACHE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        
        return data
    except Exception as e:
        debug_log(f"Error fetching manifest data: {e}")
        console.print(f"[error]Failed to fetch manifest data: {e}[/error]")
        return {}

def show_version_menu(platform: str, manifest_data: dict) -> Optional[str]:
    """Show version selection menu for a platform"""
    versions = manifest_data.get(platform, [])
    if not versions:
        console.print(f"[error]No versions found for {platform}[/error]")
        return None
    
    console.print(Panel.fit(f"[title]Available {platform} Versions[/title]", border_style="blue"))
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="dim", width=8)
    table.add_column("Date", width=25)
    table.add_column("Manifest ID", style="highlight")
    
    for i, version in enumerate(versions, start=1):
        table.add_row(str(i), version["date"], version["id"])
    
    console.print(table)
    
    while True:
        try:
            choice = IntPrompt.ask(
                f"Select version (1-{len(versions)})",
                choices=[str(i) for i in range(1, len(versions)+1)],
                show_choices=False
            )
            selected = versions[choice - 1]
            debug_log(f"Selected version: {selected['date']} (ID: {selected['id']})")
            return selected["id"]
        except (ValueError, IndexError):
            console.print("[error]Invalid selection. Please try again.[/error]")

def debug_log(message: str, save_to_file: bool = True):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"{timestamp} - {message}"
    if DEBUG_MODE:
        console.print(f"[debug]{full_msg}[/debug]")
        if save_to_file:
            with open(os.path.join(DEBUG_FOLDER, f"debug_log_{time.strftime('%Y%m%d')}.txt"), "a", encoding="utf-8") as f:
                f.write(full_msg + "\n")

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


def check_steamcmd() -> bool:
    return shutil.which("steamcmd") is not None or os.path.exists("utils/steamcmd.exe")

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

def enableoutput(line: str) -> bool:
    skip_patterns = [
        r"\[\s*\d%\]", r"\(\d.*(?:von|of).*\)",
        r"Redirecting stderr to", r"Logging directory:",
        r"UpdateUI: skip show logo", r"^\s*$",
        r"KeyValues Error", r"src/tier1/KeyValues.cpp"
    ]
    return not any(re.search(pattern, line) for pattern in skip_patterns)

def safe_move(src_dir: str, dest_dir: str):
    for item in os.listdir(src_dir):
        s, d = os.path.join(src_dir, item), os.path.join(dest_dir, item)
        if os.path.exists(d):
            if os.path.isdir(d):
                shutil.rmtree(d)
            else:
                os.remove(d)
        shutil.move(s, d)

def abort(message: str = "Aborted."):
    console.print(f"[warning]{message}[/warning]")
    raise typer.Exit(1)

def steamcmd(username: str, password: Optional[str], manifest_id: str, depot_id: str):
    debug_log(f"Preparing SteamCMD for manifest {manifest_id} (depot {depot_id})")
    platform_folder = DEPOT_PLATFORMS.get(depot_id, "Unknown")
    version_path = os.path.join(VERSIONS_DIR, platform_folder, manifest_id)
    os.makedirs(version_path, exist_ok=True)

    steamcmd_path = "utils/steamcmd.exe" if os.path.exists("utils/steamcmd.exe") else "steamcmd"
    command = [steamcmd_path, "+login", username]
    if password:
        command.append(password)
    command.extend([
        "+download_depot", APP_ID, depot_id, manifest_id,
        "+quit"
    ])
    debug_log(f"Executing: {' '.join(command)}")
    console.print("[info]Running SteamCMD...[/info]")

    depot_download_path = None
    steam_guard_sent = False

    def send_flush_after_timeout(proc):
        nonlocal steam_guard_sent
        time.sleep(10)
        if proc.poll() is None and proc.stdin:
            try:
                proc.stdin.write("\n")
                proc.stdin.flush()
                steam_guard_sent = True
                debug_log("Sent empty line to SteamCMD to flush potential Steam Guard prompt.")
            except Exception as e:
                debug_log(f"Failed to flush input to SteamCMD: {e}")

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

    threading.Thread(target=send_flush_after_timeout, args=(process,), daemon=True).start()

    while True:
        if process.stdout is None:
            break
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            line = output.strip()
            debug_log(f"SteamCMD: {line}")
            if "Steam Guard code" in line or "Steam Guard" in line:
                try:
                    steamguard_code = Prompt.ask("Enter Steam Guard code (even if already approved)")
                    if steamguard_code and process.stdin:
                        process.stdin.write(steamguard_code + "\n")
                        process.stdin.flush()
                except Exception as e:
                    debug_log(f"Steam Guard input failed: {e}")
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
            input("\nPress Enter to continue...")
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
    console.print(Panel.fit("[success]WorldBox Rewind[/success]", border_style="green"))

    if not check_steamcmd():
        console.print("[error]steamcmd not found. Ensure it exists at utils/steamcmd.exe or in your PATH.[/error]")
        raise typer.Exit(1)

    try:
        manifest_data = get_manifest_data()
        if not manifest_data:
            abort("No manifest data available. Please check your connection or the manifest source.")

        username = get_username()
        password = getpass.getpass("Steam password: ").strip()
        if not password:
            console.print("[warning]No password entered. Attempting login without it...[/warning]")

        depot_id = show_platform_menu()
        platform_name = DEPOT_PLATFORMS.get(depot_id, "Unknown")
        
        manifest_id = show_version_menu(platform_name, manifest_data)
        if not manifest_id:
            abort("No version selected.")

        version_path = os.path.join(VERSIONS_DIR, platform_name, manifest_id) # type: ignore

        if os.path.exists(version_path) and os.listdir(version_path):
            overwrite = Confirm.ask(
                f"[warning]Version {manifest_id} already exists. Redownload?[/warning]",
                default=False
            )
            if not overwrite:
                abort("Skipped existing version.")

        steamcmd(username, password, manifest_id, depot_id)  # type: ignore
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