# CCopy

**Version:** 2.0.1
**License:** Freeware (AS IS)

CCopy is a robust, safety-first command line file transfer tool designed for high-value data. Unlike standard copy commands, CCopy prioritizes data integrity over raw speed. It features atomic writes, automatic benchmarking, cryptographic verification, and progress tracking.

## ⚠️ Disclaimer

**CCopy is provided "AS IS", without warranty of any kind, express or implied.**
This includes but is not limited to the warranties of merchantability or fitness for a particular purpose. Use this software at your own risk.

## Key Features

* **Safety First:** Uses atomic writes. Files are copied to a temporary `.ccopy_tmp` file and renamed only upon successful completion. This prevents corrupt partial files at the destination if the process is interrupted.
* **Cryptographic Verification:** Supports SHA256 hashing during the copy process (inline) or after the copy is complete (post-verify).
* **Auto-Tuning:** The `--auto` mode samples the source drive, runs a benchmark, and selects the safest thread/buffer configuration for your specific hardware.
* **Smart Move:** The `--move` command strictly enforces verification. Source files are deleted only after the destination file is verified as bit-perfect.
* **Resilience:** Multi-threaded architecture with configurable buffer sizes.

## Installation

### Option A: Standalone Executable (Recommended)
If you have the compiled `.exe`, no installation is required. Simply place `ccopy.exe` in your PATH.

### Option B: Running from Source
To run the Python script directly, you need Python 3.9+ and the `tqdm` library.

```bash
pip install tqdm
python ccopy.py --help