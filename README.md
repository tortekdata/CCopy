# CCopy

Version: 2.2.0  
License: Freeware (AS IS)

CCopy is a robust, safety-first command line file transfer tool designed for high-value data.
Unlike standard copy commands, CCopy prioritizes data integrity over raw speed.

It features atomic writes, automatic benchmarking, cryptographic verification, and progress tracking.

THIS IS A STANDALONE EXECUTABLE. NO PYTHON INSTALLATION IS REQUIRED.

---

⚠️ DISCLAIMER

CCopy is provided "AS IS", without warranty of any kind, express or implied.
This includes but is not limited to the warranties of merchantability or fitness for a particular purpose.
Use this software at your own risk.

---

INSTALLATION

1. Download ccopy.exe
2. Place it in a folder of your choice (for example C:\Tools)
3. Add that folder to your system PATH to run it from anywhere
   or place the exe directly in the folder you are working in

---

COMMAND STRUCTURE

You must provide a SOURCE folder and a DESTINATION folder.
Optional ATTRIBUTES (flags) control how the program behaves.

Syntax:

    ccopy.exe [SOURCE] [DESTINATION] [ATTRIBUTES]

---

ATTRIBUTES & FLAGS REFERENCE

Flags can be freely combined. Order does not matter.

---

OPERATION MODES

(None)
Standard Copy.
Copies all files and overwrites existing ones without prompting.
Safe, but slow if files already exist.

--update
Smart Update.
Skips files that already exist at the destination with identical size and modification time.
Ideal for incremental backups.

--move
Safe Move.
Copies the file, verifies it, then deletes the source file.

NOTE:
If combined with --update, files that are skipped are NOT deleted from the source.

--dry-run
Simulation.
Scans folders and reports what would happen (file counts and sizes),
but does not copy or move any data.

---

VERIFICATION (DATA INTEGRITY)

--verify
Inline Verification.
Calculates SHA256 checksums during transfer.
Detects corruption in RAM or cables, but cannot detect disk write errors.

--verify-after
Post-Verification (RECOMMENDED).
Copies the file first, then re-reads the destination file to ensure it is bit-for-bit identical.
This is the gold standard for backups.

---

AUTOMATION & PERFORMANCE

--auto
Auto-Pilot.
Benchmarks storage, selects optimal thread and buffer settings,
and automatically enables --verify-after.

--benchmark
Speed Test.
Runs the storage benchmark and displays results in MB/s, then exits.
No files are copied.

--threads N
Force Threads.
Manually set the number of worker threads (example: --threads 4).

--buffer N
Force Buffer.
Manually set the buffer size per thread in MB (example: --buffer 8).

---

MISCELLANEOUS

--log [PATH]
Smart Logging.

If PATH is omitted:
  Auto-generates ccopy_log_DATE.txt

If PATH is a folder:
  Saves an auto-named log file inside that folder

If PATH is a file:
  Uses that exact filename

Missing directories are created automatically.

--version
Displays the current version of CCopy.

---

COMMON USAGE SCENARIOS

1. Daily Backup (Fast & Safe)

Updates the backup folder and only copies new or changed files.

    ccopy.exe "C:\Work" "D:\Backup" --auto --update --log "C:\Logs"

---

2. Move Files to Archive

Safely moves files to an external drive with full verification.

    ccopy.exe "C:\OldProjects" "F:\Archive" --move --auto --log

---

3. Simulation (Safe Test)

See what would happen without copying anything.

    ccopy.exe "C:\Source" "D:\Dest" --dry-run

---

TROUBLESHOOTING & FAQ

Q: The copy speed seems slow  
A: CCopy prioritizes safety.
For many small files, use --auto or increase --threads.
Also check if antivirus or Windows Defender is scanning each file during writes.

Q: I get "Access Denied" errors  
A: Ensure you have read permission on the source and write permission on the destination.
Try running the terminal or PowerShell as Administrator.

Q: Verification failed! What should I do?  
A: DO NOT TRUST THE COPIED DATA.
This usually indicates a hardware issue such as a bad USB cable,
failing disk, or unstable RAM. Try copying to a different drive.

Q: What do the Exit Codes mean?

Exit Codes:
0   Success – All files processed successfully
1   Error – One or more files failed
130 Aborted – User interrupted the process (CTRL+C)

---
