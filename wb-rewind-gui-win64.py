import os
import shutil
import time
import json
import threading
import subprocess
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from PIL import Image, ImageTk # type: ignore
import webbrowser

# Modern color scheme
BG_COLOR = "#f5f5f5"
PRIMARY_COLOR = "#4a6fa5"
SECONDARY_COLOR = "#6c757d"
ACCENT_COLOR = "#ff7e5f"
TEXT_COLOR = "#333333"
LIGHT_TEXT = "#000000"
DARK_BG = "#000000"  

def steamcmd_gui(username, password, manifest_id, depot_id, callback):
    """SteamCMD function to run in a thread with status messages."""
    APP_ID = "1206560"
    VERSIONS_DIR = "versions"
    DEBUG_FOLDER = "steamdb_debug"
    os.makedirs(DEBUG_FOLDER, exist_ok=True)
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

    callback(f"Running SteamCMD for manifest {manifest_id} (depot {depot_id})...")

    depot_download_path = None
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                             stdin=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)

    while True:
        if process.stdout is None:
            break
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            line = output.strip()
            if "Steam Guard code" in line or "Steam Guard" in line:
                callback("Steam Guard code required. Please enter it in the terminal.")
            elif "Depot download complete" in line:
                match = re.search(r'Depot download complete : "([^"]+)"', line)
                if match:
                    depot_download_path = re.sub(r'\\', '/', match.group(1))
                    callback(f"Download path: {depot_download_path}")
            else:
                callback(line)

    return_code = process.poll()
    if return_code != 0:
        callback("SteamCMD failed.")
        return False

    if depot_download_path and os.path.exists(depot_download_path):
        callback(f"Moving files to {version_path}...")
        try:
            for item in os.listdir(depot_download_path):
                shutil.move(os.path.join(depot_download_path, item), os.path.join(version_path, item))
            callback(f"Saved version to: {version_path}")
            try:
                shutil.rmtree(os.path.dirname(depot_download_path))
                callback(f"Cleaned up: {os.path.dirname(depot_download_path)}")
            except Exception as e:
                callback(f"Cleanup failed: {e}")
            return True
        except Exception as e:
            callback(f"Failed to move files: {e}")
            return False
    else:
        callback(f"Download path not found: {depot_download_path}")
        return False

CONFIG_PATH = os.path.join("storage", "config.json")
BACKUPS_DIR = "backups"
VERSIONS_DIR = "versions"

os.makedirs("storage", exist_ok=True)
os.makedirs("versions", exist_ok=True)
os.makedirs("versions/Linux", exist_ok=True)
os.makedirs("versions/Mac", exist_ok=True)
os.makedirs("versions/Windows", exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

class ModernButton(ttk.Button):
    """Custom styled button"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(style='Modern.TButton')

class ModernEntry(ttk.Entry):
    """Custom styled entry"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(style='Modern.TEntry')

class ModernCombobox(ttk.Combobox):
    """Custom styled combobox"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(style='Modern.TCombobox')

class WorldboxManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Worldbox Rewind Manager")
        self.root.geometry("700x500")
        self.root.minsize(600, 400)
        self.root.configure(bg=BG_COLOR)
        
        # Load config
        self.config = load_config()
        
        # Configure styles
        self.configure_styles()
        
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        self.header_frame = ttk.Frame(self.main_frame, style='Header.TFrame')
        self.header_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.title_label = ttk.Label(
            self.header_frame, 
            text="Worldbox Rewind Manager", 
            style='Header.TLabel'
        )
        self.title_label.pack(side=tk.LEFT, padx=5)
        
        # Content area
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar
        self.sidebar_frame = ttk.Frame(self.content_frame, width=150, style='Sidebar.TFrame')
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar_frame.pack_propagate(False)
        
        # Main content
        self.main_content_frame = ttk.Frame(self.content_frame, style='Content.TFrame')
        self.main_content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Create views
        self.create_sidebar()
        self.create_status_view()
        self.create_backups_view()
        self.create_versions_view()
        self.create_download_view()
        
        # Log view
        self.create_log_view()
        
        # Initialize
        self.update_status()
        self.list_versions()
        self.list_backups()
        
        # Show home view by default
        self.show_home()
    
    def configure_styles(self):
        """Configure custom styles for the application"""
        style = ttk.Style()
        
        # General styles
        style.configure('.', background=BG_COLOR, foreground=TEXT_COLOR)
        style.configure('TFrame', background=BG_COLOR)
        
        # Header style
        style.configure('Header.TFrame', background=PRIMARY_COLOR)
        style.configure('Header.TLabel', 
                       background=PRIMARY_COLOR, 
                       foreground=LIGHT_TEXT,
                       font=('Segoe UI', 12, 'bold'))
        
        # Sidebar style
        style.configure('Sidebar.TFrame', background=SECONDARY_COLOR)
        
        # Content style
        style.configure('Content.TFrame', background=BG_COLOR)
        
        # Button styles
        style.configure('Modern.TButton', 
                       background=PRIMARY_COLOR,
                       foreground=LIGHT_TEXT,
                       font=('Segoe UI', 9),
                       padding=6,
                       borderwidth=0)
        style.map('Modern.TButton',
                background=[('active', PRIMARY_COLOR), ('pressed', ACCENT_COLOR)],
                foreground=[('active', LIGHT_TEXT), ('pressed', LIGHT_TEXT)])
        
        # Entry styles
        style.configure('Modern.TEntry',
                       fieldbackground='white',
                       foreground=TEXT_COLOR,
                       padding=5,
                       bordercolor=SECONDARY_COLOR,
                       lightcolor=SECONDARY_COLOR,
                       darkcolor=SECONDARY_COLOR)
        
        # Combobox styles
        style.configure('Modern.TCombobox',
                       fieldbackground='white',
                       foreground=TEXT_COLOR,
                       selectbackground=PRIMARY_COLOR,
                       selectforeground=LIGHT_TEXT)
        
        # Listbox styles
        style.configure('Modern.TListbox',
                       background='white',
                       foreground=TEXT_COLOR,
                       selectbackground=PRIMARY_COLOR,
                       selectforeground=LIGHT_TEXT)
        
        # Debug window styles
        style.configure('Debug.TFrame', background=DARK_BG)
        style.configure('Debug.TLabel', 
                       background=DARK_BG,
                       foreground=LIGHT_TEXT)
        
        # Close button style
        style.configure('Close.TButton',
                       background=DARK_BG,
                       foreground=LIGHT_TEXT,
                       borderwidth=0,
                       padding=0)
    
    def create_sidebar(self):
        """Create the sidebar navigation"""
        buttons = [
            ("🏠 Home", self.show_home),
            ("📂 Set Path", self.set_path),
            ("💾 Backup", self.backup),
            ("📋 Versions", self.list_versions),
            ("🔄 Restore", self.list_backups),
            ("⏪ Downgrade", self.downgrade_version),
            ("⬇️ Download", self.show_download_view),
        ]
        
        for text, command in buttons:
            btn = ModernButton(
                self.sidebar_frame, 
                text=text, 
                command=command
            )
            btn.pack(fill=tk.X, padx=5, pady=3, ipady=3)
    
    def create_status_view(self):
        """Create the home/status view"""
        self.status_frame = ttk.Frame(self.main_content_frame)
        
        # Status cards
        card_frame = ttk.Frame(self.status_frame)
        card_frame.pack(fill=tk.X, pady=10)
        
        # Path card
        path_card = ttk.Frame(card_frame, style='Card.TFrame')
        path_card.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(path_card, text="Installation Path", style='CardTitle.TLabel').pack(anchor=tk.W)
        self.path_label = ttk.Label(path_card, text="Not set", style='CardValue.TLabel')
        self.path_label.pack(anchor=tk.W)
        
        # Backup card
        backup_card = ttk.Frame(card_frame, style='Card.TFrame')
        backup_card.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(backup_card, text="Last Backup", style='CardTitle.TLabel').pack(anchor=tk.W)
        self.last_backup_label = ttk.Label(backup_card, text="None", style='CardValue.TLabel')
        self.last_backup_label.pack(anchor=tk.W)
        
        # Version card
        version_card = ttk.Frame(card_frame, style='Card.TFrame')
        version_card.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(version_card, text="Current Version", style='CardTitle.TLabel').pack(anchor=tk.W)
        self.current_version_label = ttk.Label(version_card, text="Unknown", style='CardValue.TLabel')
        self.current_version_label.pack(anchor=tk.W)
        
        # Quick actions
        action_frame = ttk.Frame(self.status_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ModernButton(
            action_frame,
            text="Quick Backup",
            command=self.backup
        ).pack(side=tk.LEFT, padx=5)
        
        ModernButton(
            action_frame,
            text="Toggle Debug",
            command=self.toggle_debug
        ).pack(side=tk.LEFT, padx=5)
    
    def create_backups_view(self):
        """Create the backups view"""
        self.backups_frame = ttk.Frame(self.main_content_frame)
        
        # Title
        ttk.Label(self.backups_frame, text="Backups", style='SectionTitle.TLabel').pack(anchor=tk.W, pady=5)
        
        # List with scrollbar
        list_frame = ttk.Frame(self.backups_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.backups_scroll = ttk.Scrollbar(list_frame)
        self.backups_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.backups_list = tk.Listbox(
            list_frame,
            yscrollcommand=self.backups_scroll.set,
            selectmode=tk.SINGLE,
            bg='white',
            fg=TEXT_COLOR,
            selectbackground=PRIMARY_COLOR,
            selectforeground=LIGHT_TEXT,
            borderwidth=1,
            relief='solid',
            highlightthickness=0
        )
        self.backups_list.pack(fill=tk.BOTH, expand=True)
        self.backups_scroll.config(command=self.backups_list.yview)
        
        # Context menu
        self.backup_menu = tk.Menu(self.root, tearoff=0, bg='white', fg=TEXT_COLOR)
        self.backup_menu.add_command(label="Restore", command=self.restore_selected_backup)
        self.backup_menu.add_command(label="Delete", command=self.delete_selected_backup)
        self.backups_list.bind("<Button-3>", self.show_backup_menu)
    
    def create_versions_view(self):
        """Create the versions view"""
        self.versions_frame = ttk.Frame(self.main_content_frame)
        
        # Title
        ttk.Label(self.versions_frame, text="Available Versions", style='SectionTitle.TLabel').pack(anchor=tk.W, pady=5)
        
        # List with scrollbar
        list_frame = ttk.Frame(self.versions_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.versions_scroll = ttk.Scrollbar(list_frame)
        self.versions_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.versions_list = tk.Listbox(
            list_frame,
            yscrollcommand=self.versions_scroll.set,
            selectmode=tk.SINGLE,
            bg='white',
            fg=TEXT_COLOR,
            selectbackground=PRIMARY_COLOR,
            selectforeground=LIGHT_TEXT,
            borderwidth=1,
            relief='solid',
            highlightthickness=0
        )
        self.versions_list.pack(fill=tk.BOTH, expand=True)
        self.versions_scroll.config(command=self.versions_list.yview)
        
        # Context menu
        self.version_menu = tk.Menu(self.root, tearoff=0, bg='white', fg=TEXT_COLOR)
        self.version_menu.add_command(label="Downgrade", command=self.downgrade_selected_version)
        self.version_menu.add_command(label="Delete", command=self.delete_selected_version)
        self.versions_list.bind("<Button-3>", self.show_version_menu)
    
    def create_download_view(self):
        """Create the version download view"""
        self.download_frame = ttk.Frame(self.main_content_frame)
        
        # Title
        ttk.Label(self.download_frame, text="Download Version", style='SectionTitle.TLabel').pack(anchor=tk.W, pady=5)
        
        # Form frame
        form_frame = ttk.Frame(self.download_frame)
        form_frame.pack(fill=tk.X, pady=5)
        
        # Username
        ttk.Label(form_frame, text="Steam Username:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.username_entry = ModernEntry(form_frame)
        self.username_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3)
        
        # Password
        ttk.Label(form_frame, text="Steam Password:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.password_entry = ModernEntry(form_frame, show="*")
        self.password_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=3)
        
        # Platform
        ttk.Label(form_frame, text="Platform:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.platform_combo = ModernCombobox(form_frame, values=["Windows", "Linux", "Mac"], state="readonly")
        self.platform_combo.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=3)
        self.platform_combo.current(0)
        
        # Manifest ID
        ttk.Label(form_frame, text="Manifest ID:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=3)
        self.manifest_entry = ModernEntry(form_frame)
        self.manifest_entry.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=3)
        
        # Tutorial
        tutorial_frame = ttk.Frame(self.download_frame, style='Card.TFrame')
        tutorial_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(tutorial_frame, text="How to find a Manifest ID:", style='CardTitle.TLabel').pack(anchor=tk.W, padx=5, pady=(5,0))
        
        tutorial_text = (
            "1. Visit SteamDB WorldBox depot for your platform\n"
            "2. Copy the Manifest ID from the list"
        )
        ttk.Label(tutorial_frame, text=tutorial_text).pack(anchor=tk.W, padx=5, pady=(0,5))
        
        # Links
        links_frame = ttk.Frame(self.download_frame)
        links_frame.pack(fill=tk.X, pady=5)
        
        platforms = [
            ("Windows", "https://steamdb.info/depot/1206561/manifests/"),
            ("Linux", "https://steamdb.info/depot/1206562/manifests/"),
            ("Mac", "https://steamdb.info/depot/1206563/manifests/")
        ]
        
        for platform, url in platforms:
            btn = ModernButton(
                links_frame,
                text=platform,
                command=lambda u=url: webbrowser.open(u)
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # Download button
        ModernButton(
            self.download_frame,
            text="Download Version",
            command=self.download_version
        ).pack(pady=10)
        
        # Configure grid weights
        form_frame.grid_columnconfigure(1, weight=1)
    
    def create_log_view(self):
        """Create the debug log view"""
        self.log_frame = ttk.Frame(self.root, style='Debug.TFrame')
        self.log_frame.pack_propagate(False)
        
        # Title bar
        title_frame = ttk.Frame(self.log_frame, style='Debug.TFrame')
        title_frame.pack(fill=tk.X)
        
        ttk.Label(title_frame, text="Debug Log", style='Debug.TLabel').pack(side=tk.LEFT, padx=5, pady=2)
        
        close_btn = ttk.Button(
            title_frame,
            text="×",
            command=self.toggle_debug,
            style='Close.TButton'
        )
        close_btn.pack(side=tk.RIGHT, padx=2)
        
        # Log content
        self.log_text = scrolledtext.ScrolledText(
            self.log_frame,
            wrap=tk.WORD,
            height=8,
            state='disabled',
            bg=DARK_BG,
            fg=LIGHT_TEXT,
            insertbackground=LIGHT_TEXT,
            selectbackground=PRIMARY_COLOR,
            selectforeground=LIGHT_TEXT,
            borderwidth=0
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Start with log hidden
        self.log_visible = False
        self.log_frame.pack_forget()
    
    def toggle_debug(self):
        """Toggle the debug log visibility"""
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_frame.pack(fill=tk.X, before=self.main_frame, padx=10, pady=(0, 10))
        else:
            self.log_frame.pack_forget()
    
    def append_log(self, message):
        """Append a message to the debug log"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
    
    def update_status(self):
        """Update the status information"""
        path = self.config.get("installation_path", "Not set")
        self.path_label.config(text=path)
        
        backups = sorted(os.listdir(BACKUPS_DIR)) if os.path.exists(BACKUPS_DIR) else []
        last_backup = backups[-1] if backups else "None"
        self.last_backup_label.config(text=last_backup)
    
    def show_home(self):
        """Show the home/status view"""
        self.hide_all_views()
        self.status_frame.pack(fill=tk.BOTH, expand=True)
    
    def show_backups_view(self):
        """Show the backups view"""
        self.hide_all_views()
        self.backups_frame.pack(fill=tk.BOTH, expand=True)
    
    def show_versions_view(self):
        """Show the versions view"""
        self.hide_all_views()
        self.versions_frame.pack(fill=tk.BOTH, expand=True)
    
    def show_download_view(self):
        """Show the download view"""
        self.hide_all_views()
        self.download_frame.pack(fill=tk.BOTH, expand=True)
    
    def hide_all_views(self):
        """Hide all content views"""
        for frame in [
            self.status_frame,
            self.backups_frame,
            self.versions_frame,
            self.download_frame
        ]:
            frame.pack_forget()
    
    def set_path(self):
        """Set the installation path"""
        path = filedialog.askdirectory(title="Select Worldbox Installation Folder")
        if path:
            self.config["installation_path"] = path
            save_config(self.config)
            self.update_status()
    
    def backup(self):
        """Create a backup of the current installation"""
        installation_path = self.config.get("installation_path")
        if not installation_path or not os.path.exists(installation_path):
            messagebox.showerror("Error", "Please set a valid installation path first")
            return

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_path = os.path.join(BACKUPS_DIR, f"backup-{timestamp}")
        
        try:
            shutil.copytree(installation_path, backup_path)
            messagebox.showinfo("Success", f"Successfully created backup: {backup_path}")
            self.update_status()
            self.list_backups()
        except Exception as e:
            messagebox.showerror("Error", f"Backup failed: {str(e)}")
    
    def list_backups(self):
        """List all available backups"""
        self.backups_list.delete(0, tk.END)
        
        if os.path.exists(BACKUPS_DIR):
            backups = sorted(os.listdir(BACKUPS_DIR))
            if backups:
                for backup in backups:
                    self.backups_list.insert(tk.END, backup)
        
        self.show_backups_view()
    
    def list_versions(self):
        """List all available versions"""
        self.versions_list.delete(0, tk.END)
        
        if os.path.exists(VERSIONS_DIR):
            platforms = sorted(os.listdir(VERSIONS_DIR))
            for platform in platforms:
                self.versions_list.insert(tk.END, f"--- {platform} ---")
                versions_path = os.path.join(VERSIONS_DIR, platform)
                versions = sorted(os.listdir(versions_path)) if os.path.exists(versions_path) else []
                for version in versions:
                    self.versions_list.insert(tk.END, f"  {version}")
        
        self.show_versions_view()
    
    def show_backup_menu(self, event):
        """Show context menu for backups"""
        try:
            selection = self.backups_list.curselection()
            if selection:
                self.backup_menu.tk_popup(event.x_root, event.y_root)
        except:
            pass
    
    def show_version_menu(self, event):
        """Show context menu for versions"""
        try:
            selection = self.versions_list.curselection()
            if selection and not self.versions_list.get(selection).startswith("---"):
                self.version_menu.tk_popup(event.x_root, event.y_root)
        except:
            pass
    
    def restore_selected_backup(self):
        """Restore the selected backup"""
        selection = self.backups_list.curselection()
        if not selection:
            return
        
        backup_name = self.backups_list.get(selection)
        self.restore_backup(backup_name)
    
    def restore_backup(self, backup_name):
        """Restore a backup"""
        installation_path = self.config.get("installation_path")
        if not installation_path:
            messagebox.showerror("Error", "Please set the installation path first")
            return

        if not messagebox.askyesno(
            "Confirm", 
            f"Restore backup {backup_name}?\nThis will overwrite your current installation."
        ):
            return

        source_path = os.path.join(BACKUPS_DIR, backup_name)
        try:
            # Clear destination
            for item in os.listdir(installation_path):
                item_path = os.path.join(installation_path, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            
            # Copy from backup
            for item in os.listdir(source_path):
                s = os.path.join(source_path, item)
                d = os.path.join(installation_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            
            messagebox.showinfo("Success", f"Successfully restored backup: {backup_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore backup: {str(e)}")
    
    def delete_selected_backup(self):
        """Delete the selected backup"""
        selection = self.backups_list.curselection()
        if not selection:
            return
        
        backup_name = self.backups_list.get(selection)
        self.delete_backup(backup_name)
    
    def delete_backup(self, backup_name):
        """Delete a backup"""
        if not messagebox.askyesno(
            "Confirm", 
            f"Delete backup {backup_name}?\nThis action cannot be undone."
        ):
            return

        backup_path = os.path.join(BACKUPS_DIR, backup_name)
        try:
            if os.path.isdir(backup_path):
                shutil.rmtree(backup_path)
            else:
                os.remove(backup_path)
            self.list_backups()
            messagebox.showinfo("Success", f"Deleted backup: {backup_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete backup: {str(e)}")
    
    def downgrade_selected_version(self):
        """Downgrade to the selected version"""
        selection = self.versions_list.curselection()
        if not selection:
            return
        
        version_line = self.versions_list.get(selection)
        if version_line.startswith("---"):
            return
        
        # Find the platform by looking for the previous section header
        platform = None
        for i in range(selection[0], -1, -1):
            line = self.versions_list.get(i)
            if line.startswith("---"):
                platform = line.replace("---", "").replace("---", "").strip()
                break
        
        if not platform:
            messagebox.showerror("Error", "Could not determine platform for this version")
            return
        
        version = version_line.strip()
        self.downgrade_to_version(platform, version)
    
    def downgrade_version(self):
        """Show the downgrade version dialog"""
        if not os.path.exists(VERSIONS_DIR):
            messagebox.showerror("Error", "Versions directory not found")
            return

        platforms = sorted(os.listdir(VERSIONS_DIR))
        if not platforms:
            messagebox.showerror("Error", "No platforms available")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Downgrade Version")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("400x300")
        
        # Platform selection
        ttk.Label(dialog, text="Platform:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        platform_var = tk.StringVar()
        platform_combo = ModernCombobox(dialog, textvariable=platform_var, values=platforms, state="readonly")
        platform_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        platform_combo.current(0)
        
        # Version list
        ttk.Label(dialog, text="Available Versions:").grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        versions_frame = ttk.Frame(dialog)
        versions_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.NSEW)
        
        versions_scroll = ttk.Scrollbar(versions_frame)
        versions_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        versions_list = tk.Listbox(
            versions_frame,
            yscrollcommand=versions_scroll.set,
            selectmode=tk.SINGLE,
            bg='white',
            fg=TEXT_COLOR,
            selectbackground=PRIMARY_COLOR,
            selectforeground=LIGHT_TEXT
        )
        versions_list.pack(fill=tk.BOTH, expand=True)
        
        versions_scroll.config(command=versions_list.yview)
        
        # Update versions list when platform changes
        def update_versions(*args):
            versions_list.delete(0, tk.END)
            platform = platform_var.get()
            versions_path = os.path.join(VERSIONS_DIR, platform)
            if os.path.exists(versions_path):
                versions = sorted(os.listdir(versions_path), reverse=True)
                for version in versions:
                    versions_list.insert(tk.END, version)
        
        platform_var.trace("w", update_versions)
        update_versions()
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        def on_downgrade():
            selection = versions_list.curselection()
            if not selection:
                messagebox.showerror("Error", "Please select a version")
                return
            
            version = versions_list.get(selection)
            platform = platform_var.get()
            dialog.destroy()
            self.downgrade_to_version(platform, version)
        
        ModernButton(
            button_frame,
            text="Downgrade",
            command=on_downgrade
        ).pack(side=tk.LEFT, padx=5)
        
        ModernButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        dialog.grid_columnconfigure(1, weight=1)
        dialog.grid_rowconfigure(2, weight=1)
        
        dialog.wait_window()
    
    def downgrade_to_version(self, platform, version):
        """Downgrade to a specific version"""
        installation_path = self.config.get("installation_path")
        if not installation_path:
            messagebox.showerror("Error", "Installation path not set")
            return

        if not messagebox.askyesno(
            "Confirm", 
            f"Downgrade to version {version} for {platform}?\nThis will overwrite your current installation."
        ):
            return

        source_path = os.path.join(VERSIONS_DIR, platform, version)
        try:
            # Clear destination
            for item in os.listdir(installation_path):
                item_path = os.path.join(installation_path, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            
            # Copy from version
            for item in os.listdir(source_path):
                s = os.path.join(source_path, item)
                d = os.path.join(installation_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            
            messagebox.showinfo("Success", f"Successfully downgraded to version {version} for {platform}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to downgrade: {str(e)}")
    
    def delete_selected_version(self):
        """Delete the selected version"""
        selection = self.versions_list.curselection()
        if not selection:
            return
        
        version_line = self.versions_list.get(selection)
        if version_line.startswith("---"):
            return
        
        # Find the platform by looking for the previous section header
        platform = None
        for i in range(selection[0], -1, -1):
            line = self.versions_list.get(i)
            if line.startswith("---"):
                platform = line.replace("---", "").replace("---", "").strip()
                break
        
        if not platform:
            messagebox.showerror("Error", "Could not determine platform for this version")
            return
        
        version = version_line.strip()
        self.delete_version(platform, version)
    
    def delete_version(self, platform, version):
        """Delete a version"""
        if not messagebox.askyesno(
            "Confirm", 
            f"Delete version {version} for platform {platform}?\nThis action cannot be undone."
        ):
            return

        version_path = os.path.join(VERSIONS_DIR, platform, version)
        try:
            if os.path.isdir(version_path):
                shutil.rmtree(version_path)
            else:
                os.remove(version_path)
            self.list_versions()
            messagebox.showinfo("Success", f"Deleted version: {version} for platform {platform}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete version: {str(e)}")
    
    def download_version(self):
        """Download a version using SteamCMD"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        platform = self.platform_combo.get()
        manifest_id = self.manifest_entry.get().strip()

        if not username:
            messagebox.showerror("Error", "Steam username is required")
            return
        if not platform:
            messagebox.showerror("Error", "Platform selection is required")
            return
        if not manifest_id:
            messagebox.showerror("Error", "Manifest ID is required")
            return

        depot_id_map = {"Windows": "1206561", "Linux": "1206562", "Mac": "1206563"}
        depot_id = depot_id_map.get(platform)
        if not depot_id:
            messagebox.showerror("Error", "Invalid platform selected")
            return

        self.config["username"] = username
        save_config(self.config)

        if not messagebox.askokcancel(
            "Confirm", 
            "Please confirm on your Steam Guard app if enabled.\nClick OK to proceed with download."
        ):
            return

        self.append_log(f"Starting download for manifest {manifest_id}...")

        def callback(message):
            self.append_log(message)

        def run_steamcmd():
            success = steamcmd_gui(username, password, manifest_id, depot_id, callback)
            if success:
                self.append_log(f"Download completed successfully for manifest {manifest_id}")
                messagebox.showinfo("Download Complete", f"Version {manifest_id} downloaded successfully!")
                self.list_versions()
                self.show_versions_view()
            else:
                self.append_log("Download failed. See messages above.")
                messagebox.showerror("Download Failed", f"Failed to download version {manifest_id}")

        threading.Thread(target=run_steamcmd, daemon=True).start()

def main():
    root = tk.Tk()
    
    # Set window icon if available
    try:
        root.iconbitmap('worldbox.ico')  # Replace with your icon file
    except:
        pass
    
    # Set theme (requires ttkthemes or similar)
    try:
        from ttkthemes import ThemedStyle
        style = ThemedStyle(root)
        style.set_theme("arc")  # One of the modern themes
    except:
        pass
    
    app = WorldboxManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()