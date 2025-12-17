# CCopy

**Version:** 2.0.1
**License:** Freeware (AS IS)

CCopy is a robust, safety-first command line file transfer tool designed for high-value data. Unlike standard copy commands, CCopy prioritizes data integrity over raw speed. It features atomic writes, automatic benchmarking, cryptographic verification, and progress tracking.

**This is a standalone executable. No Python installation is required.**

## ⚠️ Disclaimer

**CCopy is provided "AS IS", without warranty of any kind, express or implied.**
This includes but is not limited to the warranties of merchantability or fitness for a particular purpose. Use this software at your own risk.

## Installation

1.  Download `ccopy.exe`.
2.  Place it in a folder of your choice (e.g., `C:\Tools`).
3.  Add that folder to your system's PATH to run it from anywhere, or place it in the folder you are working in.

## Command Structure

To use CCopy, you must provide the **Source** folder and the **Destination** folder. You can then add optional **Attributes** (flags) to change how the program behaves.

```text
ccopy.exe [SOURCE] [DESTINATION] [ATTRIBUTES]

## 📋 Attributes & Flags Reference

You can combine these flags to customize behavior. The order of flags does not matter.

### 🔹 Operation Modes

| Attribute | Description |
| :--- | :--- |
| **(None)** | **Standard Copy.** Copies all files. Overwrites files at the destination without asking. Safe, but slow if files already exist. |
| `--update` | **Smart Update.** Skips the file if it already exists at the destination with the exact same size and modification time. Saves massive amounts of time on repeated backups. |
| `--move` | **Safe Move.** Copies the file, verifies it, and *then* deletes the original from the source. <br>⚠️ *Note:* If combined with `--update`, files that are skipped (because they exist) are **not** deleted from the source for safety. |
| `--dry-run` | **Simulation.** Scans the folders and reports what *would* happen (file counts, sizes), but does not physically copy or move any data. |

### 🔹 Verification (Data Integrity)

| Attribute | Description |
| :--- | :--- |
| `--verify` | **Inline Verification.** Calculates SHA256 checksums *while* reading/writing. Detects corruption in RAM or cables, but cannot detect disk write errors. |
| `--verify-after` | **Post-Verification (Recommended).** Copies the file first, then reads it back from the destination disk to ensure it is bit-for-bit identical to the source. The gold standard for backups. |

### 🔹 Automation & Performance

| Attribute | Description |
| :--- | :--- |
| `--auto` | **Auto-Pilot.** Runs a quick storage benchmark before starting. Automatically selects the safest and most efficient thread/buffer combination for your hardware. Activates `--verify-after`. |
| `--benchmark` | **Speed Test.** Runs the storage benchmark and displays the results (MB/s), then exits. Does not copy files. |
| `--threads N` | **Force Threads.** Manually set the number of parallel worker threads (e.g., `--threads 4`). |
| `--buffer N` | **Force Buffer.** Manually set the memory buffer size per thread in MB (e.g., `--buffer 8`). |

### 🔹 Misc

| Attribute | Description |
| :--- | :--- |
| `--log FILE` | **Logging.** Writes a detailed operation log to the specified text file (e.g., `--log backup_log.txt`). |
| `--version` | **Info.** Displays the current version of CCopy. |

---

## 💡 Common Usage Scenarios

### 1. Daily Backup (Fast & Safe)
Updates your backup folder. Only copies new or changed files.
```bat
ccopy.exe "C:\Work" "D:\Backup" --auto --update



You can combine these flags to customize behavior.