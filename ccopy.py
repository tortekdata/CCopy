#!/usr/bin/env python3
"""
CCopy – smart copy/move tool with progress, benchmark, auto mode and verification

License: Freeware
AS IS – No warranty. Use at your own risk.
"""

import sys
import os
import time
import argparse
import hashlib
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

# ============================================================
# VERSION / LICENSE
# ============================================================

__version__ = "2.1.1"
__license__ = "Freeware"

# ============================================================
# CONFIG
# ============================================================

MAX_SAMPLE_BYTES = 1 * 1024**3   # 1 GB
MAX_SAMPLE_FILES = 100
DEFAULT_BUFFER_MB = 1
DEFAULT_THREADS = 1
MIN_PYTHON = (3, 9)

# ============================================================
# OPTIONAL DEPENDENCIES (FALLBACK SYSTEM)
# ============================================================

try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, iterable=None, total=0, **kwargs):
            self.iterable = iterable
            self.total = total or (len(iterable) if iterable else 0)
            self.n = 0
            print(f"Processing... (Install 'tqdm' for progress bar)")

        def __iter__(self):
            for item in self.iterable:
                yield item
                self.update()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            print("\nDone.")

        def update(self, n=1):
            pass
        
        @staticmethod
        def format_bytes(size):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} PB"

# ============================================================
# GLOBALS
# ============================================================

lock = Lock()
logger = logging.getLogger("ccopy")

# ============================================================
# UTIL
# ============================================================

def running_as_exe():
    return getattr(sys, "frozen", False)


def fatal(msg, code=1):
    logger.error(msg)
    sys.exit(code)

# ============================================================
# PREFLIGHT CHECKS
# ============================================================

def check_python():
    if sys.version_info < MIN_PYTHON:
        fatal(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required")


def validate_args(args, parser):
    if not args.source or not args.dest:
        parser.error("Both source and destination are required")

    if args.verify and args.verify_after:
        parser.error("--verify and --verify-after cannot be used together")

    if args.ask and not args.benchmark:
        parser.error("--ask requires --benchmark")

    if args.auto and args.ask:
        parser.error("--auto cannot be combined with --ask")

    if args.move and not (args.verify or args.verify_after):
        logger.warning("--move without verification is unsafe. Forcing --verify-after.")
        args.verify_after = True
    
    if args.move and args.update:
        logger.warning("--move and --update combined: Files that are skipped (up-to-date) will NOT be deleted from source.")


def check_paths(src: Path, dst: Path):
    if not src.exists():
        fatal(f"Source does not exist: {src}")
    if not src.is_dir():
        fatal("Source must be a directory")

    try:
        dst.relative_to(src)
        fatal("Destination cannot be inside source directory")
    except ValueError:
        pass

# ============================================================
# LOGGING
# ============================================================

def setup_logging(logfile=None, level="info"):
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    if logfile:
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG if level == "debug" else logging.INFO)
        logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.WARNING)
    logger.addHandler(ch)

# ============================================================
# FILE COLLECTION
# ============================================================

def collect_files(base: Path):
    result = []
    SKIP_DIRS = {
        "System Volume Information",
        "$RECYCLE.BIN",
        "Config.Msi",
        "$WinREAgent",
        "Recovery"
    }

    for root, dirs, names in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for n in names:
            p = Path(root) / n
            try:
                size = p.stat().st_size
                result.append((p, size))
            except OSError as e:
                logger.warning(f"Skipping unreadable file: {p} ({e})")
    return result

# ============================================================
# SAMPLING
# ============================================================

def sample_files(file_entries):
    sample = []
    total = 0

    for path, size in file_entries:
        if total + size > MAX_SAMPLE_BYTES:
            break
        sample.append((path, size))
        total += size
        if len(sample) >= MAX_SAMPLE_FILES:
            break

    return sample, total

# ============================================================
# HASHING
# ============================================================

def sha256_stream(path, buf):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(buf):
            h.update(chunk)
    return h.hexdigest()

# ============================================================
# COPY WORKER
# ============================================================

def copy_file(src, dst, size, buf, total_bar, do_verify, update_mode):
    """
    Returns: 0=Failed, 1=Copied, 2=Skipped
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    src_stat = src.stat()

    # --update check --
    if update_mode and dst.exists():
        try:
            dst_stat = dst.stat()
            # Check size and time (allow 2 seconds diff)
            if dst_stat.st_size == size and abs(src_stat.st_mtime - dst_stat.st_mtime) < 2.0:
                with lock:
                    total_bar.update(size)
                return 2 # Skipped
        except OSError:
            pass 

    # Normal Copy
    tmp = dst.with_suffix(dst.suffix + ".ccopy_tmp")
    h = hashlib.sha256() if do_verify else None

    try:
        with open(src, "rb") as fs, open(tmp, "wb") as fd:
            while chunk := fs.read(buf):
                fd.write(chunk)
                if h:
                    h.update(chunk)
                with lock:
                    total_bar.update(len(chunk))

        tmp.replace(dst)
        
        # KEY FIX: Copy timestamp from source to dest
        os.utime(dst, (src_stat.st_atime, src_stat.st_mtime))

        if do_verify:
            if h.hexdigest() != sha256_stream(dst, buf):
                raise RuntimeError("Verification failed")

        return 1 # Copied

    except Exception as e:
        logger.error(f"Copy failed: {src} -> {dst} ({e})")
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return 0 # Failed

# ============================================================
# BENCHMARK
# ============================================================

def benchmark(sample, buf, verify):
    start = time.time()
    total = 0
    for f, size in sample:
        try:
            with open(f, "rb") as fd:
                while fd.read(buf): pass
            if verify: sha256_stream(f, buf)
            total += size
        except OSError: pass
    elapsed = time.time() - start
    return (total / 1024**2) / elapsed if elapsed > 0 else 0

# ============================================================
# INTERACTIVE PROMPT
# ============================================================

def ask(prompt):
    try:
        ans = input(prompt).strip().lower()
        return ans in ("", "y", "yes")
    except KeyboardInterrupt:
        return False

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(prog="ccopy")
    parser.add_argument("source", type=Path)
    parser.add_argument("dest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--ask", action="store_true")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-after", action="store_true")
    parser.add_argument("--move", action="store_true")
    parser.add_argument("--update", action="store_true", help="Skip files that exist with same size/time")
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS)
    parser.add_argument("--buffer", type=int, default=DEFAULT_BUFFER_MB)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--log-level", choices=["info", "debug"], default="info")
    parser.add_argument("--version", action="version", version=f"CCopy {__version__} ({__license__})")

    args = parser.parse_args()
    check_python()
    validate_args(args, parser)
    check_paths(args.source, args.dest)
    setup_logging(args.log, args.log_level)

    logger.info(f"CCopy {__version__} started")

    # ---- SCAN ----
    files = collect_files(args.source)
    total_bytes = sum(size for _, size in files)
    if not files:
        print("No files found.")
        sys.exit(0)

    sample, sample_bytes = sample_files(files)

    # ---- DRY RUN ----
    if args.dry_run:
        print(f"\nDry-run summary")
        print(f"Files: {len(files)} / {total_bytes / 1024**3:.2f} GB")
        sys.exit(0)

    # ---- BENCHMARK / AUTO ----
    if args.benchmark or args.auto:
        print("\nBenchmarking...")
        results = []
        for t in (1, 2, 4):
            for b in (1, 2):
                speed = benchmark(sample, b*1024*1024, args.verify)
                results.append((t, b, speed))
        
        safe = min(results, key=lambda x: abs(x[0]-2) + abs(x[1]-2))
        
        if args.benchmark:
            for t, b, s in results: print(f"T={t} B={b}MB -> {s:.1f} MB/s")
        
        print(f"\nRecommended SAFE: --threads {safe[0]} --buffer {safe[1]} --verify-after")
        
        if args.auto:
            args.threads, args.buffer = safe[0], safe[1]
            args.verify_after = True

    # ---- COPY ----
    buf = args.buffer * 1024 * 1024
    copied = [] # List of (src, dst) that were ACTUALLY copied
    
    print("\nRunning CCopy")
    print(f"Threads: {args.threads}, Update: {args.update}, Verify: {args.verify_after or args.verify}")
    print(f"Mode: {'MOVE' if args.move else 'COPY'}\n")

    success_count = 0
    fail_count = 0
    skipped_count = 0

    with tqdm(total=total_bytes, unit="B", unit_scale=True, desc="COPY") as total:
        def worker(item):
            nonlocal success_count, fail_count, skipped_count
            src, size = item
            dst = args.dest / src.relative_to(args.source)
            
            res = copy_file(src, dst, size, buf, total, args.verify, args.update)
            
            if res == 1: # Copied
                copied.append((src, dst))
                return 1
            elif res == 2: # Skipped
                skipped_count += 1
                return 2
            else: # Failed
                return 0

        with ThreadPoolExecutor(max_workers=args.threads) as ex:
            results = list(ex.map(worker, files))
            success_count = sum(1 for r in results if r == 1)
            fail_count = sum(1 for r in results if r == 0)

    # ---- VERIFY AFTER ----
    if args.verify_after and copied:
        print(f"\nPost-copy verification ({len(copied)} files)...")
        # Added Progress Bar for Verification
        with tqdm(total=len(copied), unit="file", desc="VERIFY") as pbar:
            for src, dst in copied:
                try:
                    if sha256_stream(src, buf) != sha256_stream(dst, buf):
                        logger.error(f"Verification failed: {src}")
                except OSError as e:
                    logger.error(f"Error verification: {src} ({e})")
                pbar.update(1)

    # ---- MOVE ----
    if args.move:
        for src, dst in copied:
            try:
                src.unlink()
            except OSError as e:
                logger.error(f"Delete failed: {src} ({e})")

    print(f"\n✅ Done. Copied: {success_count}, Skipped: {skipped_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()