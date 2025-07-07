import os
import shutil
import time
import json
import gi  # type: ignore

import threading
import subprocess
import re

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GLib # type: ignore

def steamcmd_gui(username, password, manifest_id, depot_id, callback):

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

class WorldboxManager(Gtk.Window):
    def __init__(self):
        super().__init__(title="Worldbox Rewind Manager")
        self.set_default_size(900, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Load CSS for styling
        self._load_css()
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.set_margin_top(10)
        header.set_margin_bottom(10)
        header.set_margin_start(10)
        header.set_margin_end(10)
        header.get_style_context().add_class("header")
        
        icon = Gtk.Image.new_from_icon_name("applications-games", Gtk.IconSize.DIALOG)
        title = Gtk.Label(label="<span size='x-large' weight='bold'>Worldbox Rewind Manager</span>", use_markup=True)
        
        header.pack_start(icon, False, False, 0)
        header.pack_start(title, False, False, 0)
        main_box.pack_start(header, False, False, 0)
        
        # Content area
        content_box = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        content_box.set_position(250)
        main_box.pack_start(content_box, True, True, 0)
        
        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sidebar.set_margin_top(10)
        sidebar.set_margin_bottom(10)
        sidebar.set_margin_start(10)
        sidebar.set_margin_end(10)
        sidebar.get_style_context().add_class("sidebar")
        
        # Buttons
        buttons = [
            ("go-home-symbolic", "Home", self.show_home),
            ("folder-symbolic", "Set Installation Path", self.set_path),
            ("document-save-symbolic", "Backup Installation", self.backup),
            ("view-list-symbolic", "List Versions", self.list_versions),
            ("document-revert-symbolic", "Restore Backup", self.restore_backup),
            ("go-down-symbolic", "Downgrade Version", self.downgrade_version),
            ("system-software-install-symbolic", "Download Version", self._on_download_clicked),
        ]
        
        for icon_name, label, callback in buttons:
            btn = self._create_button(icon_name, label)
            btn.connect("clicked", lambda btn, cb=callback: cb(btn))
            sidebar.pack_start(btn, False, False, 0)
        
        content_box.pack1(sidebar, resize=False, shrink=False)
        
        # Main content area
        self.main_content = Gtk.Stack()
        self.main_content.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.main_content.set_transition_duration(300)
        
        # Status view
        self.status_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.status_view.set_margin_top(10)
        self.status_view.set_margin_bottom(10)
        self.status_view.set_margin_start(10)
        self.status_view.set_margin_end(10)
        
        self.path_label = Gtk.Label(label="Installation Path: Not set", xalign=0)
        self.last_backup_label = Gtk.Label(label="Last Backup: None", xalign=0)
        self.current_version_label = Gtk.Label(label="Current Version: Unknown", xalign=0)

        # Toggle debug window button
        self.toggle_debug_btn = Gtk.Button(label="Toggle Debug Window")
        self.toggle_debug_btn.connect("clicked", self._on_toggle_debug_clicked)
        
        self.status_view.pack_start(self.path_label, False, False, 0)
        self.status_view.pack_start(self.last_backup_label, False, False, 0)
        self.status_view.pack_start(self.current_version_label, False, False, 0)
        self.status_view.pack_start(self.toggle_debug_btn, False, False, 0)
        
        # Backups view
        self.backups_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.backups_view.set_margin_top(10)
        self.backups_view.set_margin_bottom(10)
        self.backups_view.set_margin_start(10)
        self.backups_view.set_margin_end(10)
        
        self.backups_scrolled = Gtk.ScrolledWindow()
        self.backups_list = Gtk.ListBox()
        self.backups_scrolled.add(self.backups_list)
        self.backups_view.pack_start(self.backups_scrolled, True, True, 0)
        
        # Versions view
        self.versions_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.versions_view.set_margin_top(10)
        self.versions_view.set_margin_bottom(10)
        self.versions_view.set_margin_start(10)
        self.versions_view.set_margin_end(10)
        
        self.versions_scrolled = Gtk.ScrolledWindow()
        self.versions_list = Gtk.ListBox()
        self.versions_scrolled.add(self.versions_list)
        self.versions_view.pack_start(self.versions_scrolled, True, True, 0)
        
        # Download version view
        self.download_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.download_view.set_margin_top(10)
        self.download_view.set_margin_bottom(10)
        self.download_view.set_margin_start(10)
        self.download_view.set_margin_end(10)

        # Username entry
        username_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        username_label = Gtk.Label(label="Steam Username:", xalign=0)
        self.username_entry = Gtk.Entry()
        username_box.pack_start(username_label, False, False, 0)
        username_box.pack_start(self.username_entry, True, True, 0)
        self.download_view.pack_start(username_box, False, False, 0)

        # Password entry
        password_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        password_label = Gtk.Label(label="Steam Password:", xalign=0)
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        password_box.pack_start(password_label, False, False, 0)
        password_box.pack_start(self.password_entry, True, True, 0)
        self.download_view.pack_start(password_box, False, False, 0)

        # Platform selection
        platform_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        platform_label = Gtk.Label(label="Platform:", xalign=0)
        self.platform_combo = Gtk.ComboBoxText()
        for platform in ["Windows", "Linux", "Mac"]:
            self.platform_combo.append_text(platform)
        platform_box.pack_start(platform_label, False, False, 0)
        platform_box.pack_start(self.platform_combo, True, True, 0)
        self.download_view.pack_start(platform_box, False, False, 0)

        # Manifest ID entry
        manifest_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        manifest_label = Gtk.Label(label="Manifest ID:", xalign=0)
        self.manifest_entry = Gtk.Entry()
        manifest_box.pack_start(manifest_label, False, False, 0)
        manifest_box.pack_start(self.manifest_entry, True, True, 0)
        self.download_view.pack_start(manifest_box, False, False, 0)

        tutorial_label = Gtk.Label(label="Tutorial: How to find a Manifest ID", xalign=0)
        self.download_view.pack_start(tutorial_label, False, False, 0)
        tutorial_text = (
            "1. Visit SteamDB WorldBox depot for your platform:\n"
            "   - Windows: https://steamdb.info/depot/1206561/manifests/\n"
            "   - Linux: https://steamdb.info/depot/1206562/manifests/\n"
            "   - Mac: https://steamdb.info/depot/1206563/manifests/\n"
            "2. Copy the Manifest ID you want from the list."
        )
        tutorial_label_box = Gtk.Label()
        tutorial_label_box.set_xalign(0)
        tutorial_label_box.set_line_wrap(True)
        tutorial_label_box.set_markup(
            "1. Visit SteamDB WorldBox depot for your platform:\n"
            "   - Windows: <a href='https://steamdb.info/depot/1206561/manifests/'>https://steamdb.info/depot/1206561/manifests/</a>\n"
            "   - Linux: <a href='https://steamdb.info/depot/1206562/manifests/'>https://steamdb.info/depot/1206562/manifests/</a>\n"
            "   - Mac: <a href='https://steamdb.info/depot/1206563/manifests/'>https://steamdb.info/depot/1206563/manifests/</a>\n"
            "2. Copy the Manifest ID you want from the list."
        )
        tutorial_label_box.set_selectable(True)
        self.download_view.pack_start(tutorial_label_box, True, True, 0)

        # Download button
        download_btn = Gtk.Button(label="Download")
        download_btn.connect("clicked", self._on_download_clicked)
        self.download_view.pack_start(download_btn, False, False, 0)

        info_label = Gtk.Label(label="Enter your Steam username, password, select platform, and manifest ID to download a version.", xalign=0)
        self.download_view.pack_start(info_label, False, False, 10)

        self.main_content.add_named(self.status_view, "status")
        self.main_content.add_named(self.backups_view, "backups")
        self.main_content.add_named(self.versions_view, "versions")
        self.main_content.add_named(self.download_view, "download")

        content_box.pack2(self.main_content, resize=True, shrink=False)
        
        # Status bar, kinda broken rn
        self.status_bar = Gtk.Statusbar()
        self.status_bar_context_id = self.status_bar.get_context_id("status")
        main_box.pack_start(self.status_bar, False, False, 0)

        # Log view for displaying output logs
        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        log_scrolled = Gtk.ScrolledWindow()
        log_scrolled.set_min_content_height(50)
        log_scrolled.set_max_content_height(50)
        log_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        log_scrolled.add(self.log_view)

        self.log_revealer = Gtk.Revealer()
        self.log_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.log_revealer.set_transition_duration(300)
        self.log_revealer.add(log_scrolled)
        self.log_revealer.set_reveal_child(True)  # Initially visible

        main_box.pack_start(self.log_revealer, False, False, 0)

        # Initialize config
        self.config = load_config()
        self.update_status()
        self.list_versions(None)
        self.restore_backup(None)

    def _load_css(self):
        css = """
        .header,
        .sidebar,
        .sidebar button {
            background-color: transparent;
        }

        .sidebar button:hover {
            background-color: rgba(255, 255, 255, 0.05);
        }

        .sidebar button:active {
            background-color: rgba(255, 255, 255, 0.10);
        }               

        list {
            all: unset;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _create_button(self, icon_name, label):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        lbl = Gtk.Label(label=label, xalign=0)
        
        box.pack_start(icon, False, False, 0)
        box.pack_start(lbl, True, True, 0)
        
        btn = Gtk.Button()
        btn.add(box)
        btn.get_style_context().add_class("flat")
        return btn

    def append_log(self, message: str):
        def _append():
            end_iter = self.log_buffer.get_end_iter()
            self.log_buffer.insert(end_iter, message + "\n")
            mark = self.log_buffer.create_mark(None, self.log_buffer.get_end_iter(), False)
            self.log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        GLib.idle_add(_append)

    def _on_toggle_debug_clicked(self, widget):
        visible = self.log_revealer.get_reveal_child()
        self.log_revealer.set_reveal_child(not visible)

    def update_status(self):
        path = self.config.get("installation_path", "Not set")
        self.path_label.set_text(f"Installation Path: {path}")
        
        backups = sorted(os.listdir(BACKUPS_DIR)) if os.path.exists(BACKUPS_DIR) else []
        last_backup = backups[-1] if backups else "None"
        self.last_backup_label.set_text(f"Last Backup: {last_backup}")
        
        self.status_bar.push(self.status_bar_context_id, f"Ready | Installation: {path}")

    def show_home(self, widget):
        self.main_content.set_visible_child_name("status")

    def _on_download_clicked(self, widget):
        self.main_content.set_visible_child_name("download")

        username = self.username_entry.get_text().strip()
        password = self.password_entry.get_text()
        platform = self.platform_combo.get_active_text()
        manifest_id = self.manifest_entry.get_text().strip()

        if not username:
            self.status_bar.push(self.status_bar_context_id, "Error: Steam username is required")
            return
        if not platform:
            self.status_bar.push(self.status_bar_context_id, "Error: Platform selection is required")
            return
        if not manifest_id:
            self.status_bar.push(self.status_bar_context_id, "Error: Manifest ID is required")
            return

        depot_id_map = {"Windows": "1206561", "Linux": "1206562", "Mac": "1206563"}
        depot_id = depot_id_map.get(platform)
        if not depot_id:
            self.status_bar.push(self.status_bar_context_id, "Error: Invalid platform selected")
            return

        self.config["username"] = username
        save_config(self.config)

        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Please confirm on your Steam Guard app if enabled."
        )
        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            self.status_bar.push(self.status_bar_context_id, "Download cancelled by user.")
            return

        self.status_bar.push(self.status_bar_context_id, "Starting download...")

        def callback(message):
            self.append_log(message)

        def run_steamcmd():
            success = steamcmd_gui(username, password, manifest_id, depot_id, callback)
            if success:
                self.append_log(f"Download completed successfully for manifest {manifest_id}")
                self.list_versions(None)
                self.main_content.set_visible_child_name("versions")
            else:
                self.append_log("Download failed. See messages above.")

        threading.Thread(target=run_steamcmd, daemon=True).start()

    def set_path(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Select Worldbox Installation Folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Select", Gtk.ResponseType.OK
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            if os.path.exists(path):
                self.config["installation_path"] = path
                save_config(self.config)
                self.update_status()
        dialog.destroy()

    def backup(self, widget):
        installation_path = self.config.get("installation_path")
        if not installation_path or not os.path.exists(installation_path):
            self.status_bar.push(self.status_bar_context_id, "Error: Please set a valid installation path first")
            return

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_path = os.path.join(BACKUPS_DIR, f"backup-{timestamp}")
        
        try:
            shutil.copytree(installation_path, backup_path)
            self.status_bar.push(self.status_bar_context_id, f"Successfully created backup: {backup_path}")
            self.update_status()
            self.restore_backup(None)
        except Exception as e:
            self.status_bar.push(self.status_bar_context_id, f"Backup failed: {str(e)}")

    def list_versions(self, widget):
        for child in self.versions_list.get_children():
            self.versions_list.remove(child)
        
        if os.path.exists(BACKUPS_DIR):
            backups = sorted(os.listdir(BACKUPS_DIR))
            if backups:
                section = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                label = Gtk.Label(label="<b>Backups</b>", use_markup=True, xalign=0)
                box.pack_start(label, True, True, 0)
                section.add(box)
                self.versions_list.add(section)
                
                for backup in backups:
                    row = self._create_version_row(backup, "document-save-symbolic")
                    self.versions_list.add(row)
        
        if os.path.exists(VERSIONS_DIR):
            platforms = sorted(os.listdir(VERSIONS_DIR))
            for platform in platforms:
                section = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                label = Gtk.Label(label=f"<b>{platform} Versions</b>", use_markup=True, xalign=0)
                box.pack_start(label, True, True, 0)
                section.add(box)
                self.versions_list.add(section)
                
                versions_path = os.path.join(VERSIONS_DIR, platform)
                versions = sorted(os.listdir(versions_path)) if os.path.exists(versions_path) else []
                
                for version in versions:
                    row = self._create_version_row(version, "system-software-install-symbolic", platform)
                    self.versions_list.add(row)
        
        self.versions_list.show_all()
        self.main_content.set_visible_child_name("versions")

    def _create_version_row(self, name, icon_name, platform=None):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        lbl = Gtk.Label(label=name, xalign=0)
        
        box.pack_start(icon, False, False, 0)
        box.pack_start(lbl, True, True, 0)
        
        if platform:
            delete_btn = Gtk.Button.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
            delete_btn.set_tooltip_text("Delete this version")
            delete_btn.connect("clicked", self._on_delete_version_clicked, platform, name)
            box.pack_start(delete_btn, False, False, 0)
        
        row.add(box)
        return row

    def restore_backup(self, widget):
        for child in self.backups_list.get_children():
            self.backups_list.remove(child)
        
        backups = sorted(os.listdir(BACKUPS_DIR)) if os.path.exists(BACKUPS_DIR) else []
        if not backups:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label="No backups available")
            row.add(label)
            self.backups_list.add(row)
            self.backups_list.show_all()
            return
        
        for backup in backups:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            icon = Gtk.Image.new_from_icon_name("document-save-symbolic", Gtk.IconSize.BUTTON)
            lbl = Gtk.Label(label=backup, xalign=0)
            
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            restore_btn = Gtk.Button.new_from_icon_name("document-revert-symbolic", Gtk.IconSize.BUTTON)
            restore_btn.set_tooltip_text("Restore this backup")
            restore_btn.connect("clicked", self._on_restore_backup_clicked, backup)
            
            delete_btn = Gtk.Button.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
            delete_btn.set_tooltip_text("Delete this backup")
            delete_btn.connect("clicked", self._on_delete_backup_clicked, backup)
            
            btn_box.pack_start(restore_btn, False, False, 0)
            btn_box.pack_start(delete_btn, False, False, 0)
            
            box.pack_start(icon, False, False, 0)
            box.pack_start(lbl, True, True, 0)
            box.pack_start(btn_box, False, False, 0)
            row.add(box)
            self.backups_list.add(row)
        
        self.backups_list.show_all()
        self.main_content.set_visible_child_name("backups")

    def _on_restore_backup_clicked(self, button, backup_name):
        installation_path = self.config.get("installation_path")
        if not installation_path:
            self.status_bar.push(self.status_bar_context_id, "Error: Please set the installation path first")
            return

        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Restore backup {backup_name}?"
        )
        dialog.format_secondary_text("This will overwrite your current installation.")
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            source_path = os.path.join(BACKUPS_DIR, backup_name)
            try:
                for item in os.listdir(installation_path):
                    item_path = os.path.join(installation_path, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                
                for item in os.listdir(source_path):
                    s = os.path.join(source_path, item)
                    d = os.path.join(installation_path, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                
                self.status_bar.push(self.status_bar_context_id, f"Successfully restored backup: {backup_name}")
            except Exception as e:
                self.status_bar.push(self.status_bar_context_id, f"Failed to restore backup: {str(e)}")

    def downgrade_version(self, widget):
        if not os.path.exists(VERSIONS_DIR):
            self.status_bar.push(self.status_bar_context_id, "Error: Versions directory not found")
            return

        platforms = sorted(os.listdir(VERSIONS_DIR))
        if not platforms:
            self.status_bar.push(self.status_bar_context_id, "Error: No platforms available")
            return

        dialog = Gtk.Dialog(
            title="Downgrade Version",
            parent=self,
            modal=True,
            destroy_with_parent=True
        )
        dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Downgrade", Gtk.ResponseType.OK
        )
        dialog.set_default_size(500, 400)
        
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        
        platform_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        platform_label = Gtk.Label(label="Platform:")
        self.platform_combo_dlg = Gtk.ComboBoxText()
        
        for platform in platforms:
            self.platform_combo_dlg.append_text(platform)
        
        platform_box.pack_start(platform_label, False, False, 0)
        platform_box.pack_start(self.platform_combo_dlg, True, True, 0)
        box.pack_start(platform_box, False, False, 0)
        
        version_label = Gtk.Label(label="Available Versions:")
        box.pack_start(version_label, False, False, 0)
        
        self.version_list_dlg = Gtk.ListBox()
        self.version_list_dlg.set_selection_mode(Gtk.SelectionMode.SINGLE)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self.version_list_dlg)
        box.pack_start(scrolled, True, True, 0)
        
        self.platform_combo_dlg.connect("changed", self._update_version_list_dlg)
        self._update_version_list_dlg()
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            selected_row = self.version_list_dlg.get_selected_row()
            if selected_row:
                platform = self.platform_combo_dlg.get_active_text()
                box = selected_row.get_child()
                label = None
                for child in box.get_children():
                    if isinstance(child, Gtk.Label):
                        label = child
                        break
                if label:
                    version = label.get_text()
                else:
                    version = None
                
                if version:
                    source_path = os.path.join(VERSIONS_DIR, platform, version)
                    try:
                        installation_path = self.config.get("installation_path")
                        if not installation_path:
                            raise ValueError("Installation path not set")
                        
                        for item in os.listdir(installation_path):
                            item_path = os.path.join(installation_path, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                        
                        for item in os.listdir(source_path):
                            s = os.path.join(source_path, item)
                            d = os.path.join(installation_path, item)
                            if os.path.isdir(s):
                                shutil.copytree(s, d)
                            else:
                                shutil.copy2(s, d)
                        
                        self.status_bar.push(self.status_bar_context_id, f"Successfully downgraded to version {version} for {platform}")
                    except Exception as e:
                        self.status_bar.push(self.status_bar_context_id, f"Failed to downgrade: {str(e)}")
        
        dialog.destroy()

    def _update_version_list_dlg(self, widget=None):
        for child in self.version_list_dlg.get_children():
            self.version_list_dlg.remove(child)
        
        platform = self.platform_combo_dlg.get_active_text()
        if not platform:
            return
        
        versions_path = os.path.join(VERSIONS_DIR, platform)
        if not os.path.exists(versions_path):
            return
        
        versions = sorted(os.listdir(versions_path), reverse=True)
        for version in versions:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            icon = Gtk.Image.new_from_icon_name("system-software-install-symbolic", Gtk.IconSize.BUTTON)
            label = Gtk.Label(label=version, xalign=0)
            
            box.pack_start(icon, False, False, 0)
            box.pack_start(label, True, True, 0)
            row.add(box)
            self.version_list_dlg.add(row)
        
        self.version_list_dlg.show_all()

    def _on_delete_backup_clicked(self, button, backup_name):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete backup {backup_name}?"
        )
        dialog.format_secondary_text("This action cannot be undone.")
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            backup_path = os.path.join(BACKUPS_DIR, backup_name)
            try:
                if os.path.isdir(backup_path):
                    shutil.rmtree(backup_path)
                else:
                    os.remove(backup_path)
                self.status_bar.push(self.status_bar_context_id, f"Deleted backup: {backup_name}")
                self.restore_backup(None)
            except Exception as e:
                self.status_bar.push(self.status_bar_context_id, f"Failed to delete backup: {str(e)}")

    def _on_delete_version_clicked(self, button, platform, version):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete version {version} for platform {platform}?"
        )
        dialog.format_secondary_text("This action cannot be undone.")
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            version_path = os.path.join(VERSIONS_DIR, platform, version)
            try:
                if os.path.isdir(version_path):
                    shutil.rmtree(version_path)
                else:
                    os.remove(version_path)
                self.status_bar.push(self.status_bar_context_id, f"Deleted version: {version} for platform {platform}")
                self.list_versions(None)
            except Exception as e:
                self.status_bar.push(self.status_bar_context_id, f"Failed to delete version: {str(e)}")

def main():
    win = WorldboxManager()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()