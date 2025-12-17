#!/usr/bin/env python3
"""
CCopy – smart copy tool with progress, benchmark, auto mode and verification

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

__version__ = "2.0.0"
__license__ = "Freeware"

AS_IS_NOTICE = (
    "CCopy is freeware.\n\n"
    "This software is provided \"AS IS\", without warranty of any kind,\n"
    "express or implied, including but not limited to the warranties of\n"
    "merchantability, fitness for a particular purpose and noninfringement.\n\n"
    "Use at your own risk."
)

# ============================================================
# CONFIG
# ============================================================

MAX_SAMPLE_BYTES = 1 * 1024**3     # 1 GB
MAX_SAMPLE_FILES = 100
DEFAULT_BUFFER_MB = 1
DEFAULT_THREADS = 1
MIN_PYTHON = (3, 9)

# ============================================================
# OPTIONAL DEPENDENCIES
# ============================================================

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

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


def check_dependencies():
    if running_as_exe():
        return
    if tqdm is None:
        fatal("Missing dependency 'tqdm'. Install with: pip install tqdm")


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
        parser.error("--move requires --verify or --verify-after for safety")


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

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    )

    # File log
    if logfile:
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG if level == "debug" else logging.INFO)
        logger.addHandler(fh)

    # Console log (important messages only)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.WARNING)
    logger.addHandler(ch)

# ============================================================
# FILE SCANNING / SAMPLING
# ============================================================

def collect_files(base: Path):
    for root, _, names in os.walk(base):
        for n in names:
            yield Path(root) / n


def sample_files(files):
    sample = []
    total = 0

    for f in files:
        try:
            size = f.stat().st_size
        except OSError:
            continue

        if total + size > MAX_SAMPLE_BYTES:
            break

        sample.append((f, size))
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
# COPY WORKER (SAFE COPY + STREAMING HASH)
# ============================================================

def copy_file(src, dst, buf, total_bar, do_verify):
    tmp = dst.with_suffix(dst.suffix + ".ccopy_tmp")
    h = hashlib.sha256() if do_verify else None

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(src, "rb") as fs, open(tmp, "wb") as fd:
            while chunk := fs.read(buf):
                fd.write(chunk)
                if h:
                    h.update(chunk)
                with lock:
                    total_bar.update(len(chunk))

        tmp.replace(dst)

        if do_verify:
            if h.hexdigest() != sha256_stream(dst, buf):
                raise RuntimeError("Verification failed")

        return True

    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise

# ============================================================
# BENCHMARK
# ============================================================

def benchmark(sample, buf, verify):
    start = time.time()
    total = 0

    for f, size in sample:
        with open(f, "rb") as fd:
            while fd.read(buf):
                pass
        if verify:
            sha256_stream(f, buf)
        total += size

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
    parser = argparse.ArgumentParser(
        prog="ccopy",
        description=(
            "CCopy – smart copy tool with progress, benchmark and verification\n\n"
            "License: Freeware\n"
            "This software is provided \"AS IS\". Use at your own risk."
        )
    )

    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("dest", nargs="?", type=Path)

    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--ask", action="store_true")
    parser.add_argument("--auto", action="store_true")

    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-after", action="store_true")
    parser.add_argument("--move", action="store_true")

    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS)
    parser.add_argument("--buffer", type=int, default=DEFAULT_BUFFER_MB)

    parser.add_argument("--log", type=Path)
    parser.add_argument("--log-level", choices=["info", "debug"], default="info")

    parser.add_argument(
        "--version",
        action="version",
        version=f"CCopy {__version__} ({__license__})"
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # ---- PREFLIGHT ----
    check_python()
    check_dependencies()
    validate_args(args, parser)
    check_paths(args.source, args.dest)

    setup_logging(args.log, args.log_level)

    logger.warning("CCopy is freeware and provided AS IS. Use at your own risk.")
    logger.info(f"CCopy version {__version__} started")

    # ---- SCAN ----
    files = list(collect_files(args.source))
    sizes = []
    total_bytes = 0

    for f in files:
        try:
            s = f.stat().st_size
            sizes.append((f, s))
            total_bytes += s
        except OSError:
            pass

    sample, sample_bytes = sample_files(iter(sizes))

    # ---- DRY RUN ----
    if args.dry_run:
        print("\nDry-run summary")
        print(f"Files      : {len(sizes)}")
        print(f"Total size : {total_bytes / 1024**3:.2f} GB")
        print(f"Sample     : {len(sample)} files / {sample_bytes / 1024**2:.1f} MB")
        print(f"Intent     : {'SAFE' if args.verify or args.verify_after else 'FAST'}")
        sys.exit(0)

    # ---- BENCHMARK / AUTO ----
    if args.benchmark or args.auto:
        print("\nBenchmarking on sample...")
        results = []

        for t in (1, 2, 4):
            for b in (1, 2):
                speed = benchmark(sample, b * 1024 * 1024, args.verify)
                results.append((t, b, speed))

        best = max(results, key=lambda x: x[2])
        safe = min(results, key=lambda x: abs(x[0]-2) + abs(x[1]-2))

        print("\nResults (MB/s):")
        for t, b, s in results:
            print(f"  threads={t} buffer={b}MB -> {s:.1f}")

        print("\nRecommended FAST:")
        print(f"  --threads {best[0]} --buffer {best[1]}")

        print("Recommended SAFE:")
        print(f"  --threads {safe[0]} --buffer {safe[1]} --verify-after")

        if args.auto:
            args.threads, args.buffer = safe[0], safe[1]
            args.verify_after = True
        elif args.ask:
            if ask("\nRun with SAFE settings? [Y/n]: "):
                args.threads, args.buffer = safe[0], safe[1]
                args.verify_after = True
            else:
                sys.exit(0)
        else:
            sys.exit(0)

    # ---- COPY PHASE ----
    buf = args.buffer * 1024 * 1024
    copied = []

    print("\nRunning CCopy")
    print(f"Threads      : {args.threads}")
    print(f"Verify inline: {args.verify}")
    print(f"Verify after : {args.verify_after}")
    print(f"Mode         : {'MOVE' if args.move else 'COPY'}\n")

    with tqdm(total=total_bytes, unit="B", unit_scale=True, desc="TOTAL") as total:
        def worker(item):
            src, _ = item
            dst = args.dest / src.relative_to(args.source)

            copy_file(src, dst, buf, total, args.verify)
            copied.append((src, dst))

        with ThreadPoolExecutor(max_workers=args.threads) as ex:
            list(ex.map(worker, sizes))

    # ---- VERIFY AFTER ----
    if args.verify_after:
        print("\nPost-copy verification...")
        for src, dst in copied:
            if sha256_stream(src, buf) != sha256_stream(dst, buf):
                fatal(f"Verification failed: {src}")

    # ---- MOVE CLEANUP ----
    if args.move:
        for src, _ in copied:
            src.unlink()

    logger.info("CCopy completed successfully")
    print("\n✅ Done")


if __name__ == "__main__":
    main()
