

# 🌍 Worldbox Rewind

A simple tool to download old versions of **WorldBox** using **SteamCMD** and manifest IDs from [SteamDB](https://steamdb.info/).

</br>

## ✨ Features

* Pick a platform: Windows, Linux, or Mac
* Enter any manifest ID to download a specific version
* Step-by-step manifest guide included
* Version Manager

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

```bash
python rewind.py
```

</br>

## 📚 How to Use

1. Choose your platform (Windows, Linux, Mac).
2. Follow the instructions to find a manifest ID on SteamDB.
3. Enter the manifest ID.
4. The version will be downloaded and saved.

</br>

## 📁 Downloads Saved In

```
/versions/
  ├── Windows/
  ├── Linux/
  └── Mac/
```

</br>

## 📸 Example

```bash
$ python main.py
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
- [ ] Bulk Downloading
- [ ] Automatic ID fetching(?)
- [x] Version Manager
- [ ] GUI Version (maybe)

</br>

## ⚠️ Disclaimer

This tool only uses official SteamCMD functionality. You must own WorldBox on Steam to download any content.

