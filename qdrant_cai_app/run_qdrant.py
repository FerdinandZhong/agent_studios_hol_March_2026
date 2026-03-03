#!/usr/bin/env python3
"""
Run Qdrant vector database server as a CAI Application.

Downloads and runs Qdrant server on Linux, storing data persistently
in /home/cdsw/qdrant_data.
"""

import os
import sys
import subprocess
import urllib.request
import tarfile
from pathlib import Path


QDRANT_VERSION = "v1.13.2"
QDRANT_DATA_PATH = os.environ.get("QDRANT_DATA_PATH", "/home/cdsw/qdrant_data")
QDRANT_BIN_PATH = "/home/cdsw/.qdrant/bin"
QDRANT_PORT = "8100"
QDRANT_HOST = "127.0.0.1"


def download_qdrant() -> str:
    """Download and extract Qdrant binary for Linux x86_64."""
    print(f"Downloading Qdrant {QDRANT_VERSION}...")

    url = f"https://github.com/qdrant/qdrant/releases/download/{QDRANT_VERSION}/qdrant-x86_64-unknown-linux-musl.tar.gz"
    print(f"  URL: {url}")

    bin_dir = Path(QDRANT_BIN_PATH)
    bin_dir.mkdir(parents=True, exist_ok=True)
    tar_path = bin_dir / "qdrant.tar.gz"

    urllib.request.urlretrieve(url, tar_path)

    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(bin_dir)

    tar_path.unlink()

    qdrant_bin = bin_dir / "qdrant"
    if qdrant_bin.exists():
        qdrant_bin.chmod(0o755)
        print(f"Qdrant installed at: {qdrant_bin}")
        return str(qdrant_bin)

    raise FileNotFoundError("Qdrant binary not found after extraction")


def get_qdrant_binary() -> str:
    """Get path to Qdrant binary, downloading if necessary."""
    qdrant_bin = Path(QDRANT_BIN_PATH) / "qdrant"
    if qdrant_bin.exists():
        print(f"Qdrant already installed: {qdrant_bin}")
        return str(qdrant_bin)
    return download_qdrant()


def setup_data_directory() -> str:
    """Create data directory structure."""
    data_path = Path(QDRANT_DATA_PATH)
    (data_path / "storage").mkdir(parents=True, exist_ok=True)
    (data_path / "snapshots").mkdir(parents=True, exist_ok=True)
    print(f"Data directory: {data_path}")
    return str(data_path)


def run_qdrant(binary_path: str, data_path: str):
    """Run Qdrant server."""
    print()
    print("=" * 60)
    print(f"  Qdrant Vector Database Server")
    print(f"  Version: {QDRANT_VERSION}")
    print(f"  Host: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"  Data: {data_path}")
    print("=" * 60)
    print()

    env = os.environ.copy()
    env["QDRANT__SERVICE__HTTP_PORT"] = QDRANT_PORT
    env["QDRANT__SERVICE__HOST"] = QDRANT_HOST
    env["QDRANT__STORAGE__STORAGE_PATH"] = os.path.join(data_path, "storage")
    env["QDRANT__STORAGE__SNAPSHOTS_PATH"] = os.path.join(data_path, "snapshots")

    process = subprocess.Popen(
        [binary_path],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.rstrip())
        process.wait()
    except KeyboardInterrupt:
        print("Shutting down Qdrant...")
        process.terminate()
        process.wait()


def main():
    print()
    print("=" * 60)
    print("  Qdrant Vector Database - CAI Application")
    print("=" * 60)
    print()

    try:
        binary_path = get_qdrant_binary()
        data_path = setup_data_directory()
        run_qdrant(binary_path, data_path)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
