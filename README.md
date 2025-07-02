# 🌍 Worldbox Rewind

![alt text](assets/mewhen.png)

</br>
A simple tool to downgrade WorldBox using SteamCMD and manifest IDs because every fucking update breaks mods. Yippe.

</br>

## ✨ Features

* Pick a platform: Windows, Linux, or Mac
* Enter any manifest ID to download a specific version
* Bulk download multiple manifest IDs from a text file
* Step-by-step manifest guide included
* Version Manager with backup, restore, downgrade capabilities

</br>

## ✅ Requirements

* Python 3.8 or newer
* [SteamCMD](https://developer.valvesoftware.com/wiki/SteamCMD) installed and in your system PATH


</br>

## 🛠️ Setup

1. Clone or download this repo.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the tool:

For single or interactive download:

```bash
python rewind.py
```

For bulk downloading from a list of manifest IDs:

```bash
python bulk_rewind.py
```

For managing versions and backups:

```bash
python manager.py
```

</br>

## 📚 How to Use

### Rewind.py (Single Download)

1. Choose your platform (Windows, Linux, Mac).
2. Follow the instructions to find a manifest ID on SteamDB.
3. Enter the manifest ID.
4. The version will be downloaded and saved.

### Bulk Rewind (Bulk Download)

1. Choose your platform.
2. Provide a path to a text file containing manifest IDs (one per line).
3. The tool will download all listed versions sequentially.

### Manager.py (Version Manager)

1. Set your installation path.
2. Backup your current installation.
3. List available backups and versions.
4. Restore a backup or downgrade to a selected version.

</br>

## 📁 Downloads Saved In

```
/versions/
  ├── Windows/
  ├── Linux/
  └── Mac/
```

Backups are saved in:

```
/backups/
```

</br>

## 📸 Example

```bash
$ python rewind.py
 Worldbox Rewind
Select your platform:
1. Windows
2. Linux
3. Mac

Enter manifest ID: 1234567890123456789
Downloading...
 Successfully saved version to: versions/Windows/1234567890123456789
```

</br>

## 🔐 Steam Login

* You'll be prompted to log in with your Steam username and password.
* Steam Guard is supported (you may need to approve via mobile app).

</br>

## TODO
- [x] Bulk Downloading
- [ ] Automatic ID fetching(?)
- [x] Version Manager
- [ ] GUI Version (maybe)

</br>

## ⚠️ Disclaimer

This tool only uses official SteamCMD functionality. You must own WorldBox on Steam to download any content.
