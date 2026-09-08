"""
CaseIntel — Local Portable Neo4j Manager
Developer convenience script to ensure a local Neo4j instance is available for testing/development.
Downloads portable OpenJDK 21 and Neo4j Community Server 5.26.0 if not already installed locally,
configures credentials, and launches the server.

Endpoints:
- Bolt Protocol: bolt://localhost:7687
- Neo4j Browser: http://localhost:7474
Default Credentials:
- Username: neo4j
- Password: password
"""

import os
import sys
import time
import socket
import zipfile
import subprocess
import urllib.request
from pathlib import Path

LOCAL_DIR = Path(os.path.expanduser("~/.neo4j_local")).resolve()
JDK_ZIP_URL = "https://aka.ms/download-jdk/microsoft-jdk-21-windows-x64.zip"
NEO4J_ZIP_URL = "https://dist.neo4j.org/neo4j-community-5.26.0-windows.zip"

BOLT_PORT = 7687
HTTP_PORT = 7474


def is_port_open(host="localhost", port=BOLT_PORT) -> bool:
    """Check if a port is actively accepting TCP connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        res = s.connect_ex((host, port))
        return res == 0
    finally:
        s.close()


def download_with_progress(url: str, dest_path: Path):
    """Download a file showing progress."""
    print(f"[Neo4j Setup] Downloading {url} -> {dest_path.name}...")
    req = urllib.request.Request(url, headers={"User-Agent": "CaseIntel-Setup"})
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out_f:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1MB
        last_pct = -1
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = int((downloaded / total) * 100)
                if pct != last_pct and pct % 10 == 0:
                    print(f"  Downloaded {pct}% ({downloaded // (1024*1024)}MB / {total // (1024*1024)}MB)...")
                    last_pct = pct
    print(f"[Neo4j Setup] Download complete: {dest_path.name}")


def extract_zip(zip_path: Path, target_dir: Path):
    """Extract zip archive."""
    print(f"[Neo4j Setup] Extracting {zip_path.name} to {target_dir}...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_dir)
    print(f"[Neo4j Setup] Extraction complete.")


def find_java_home(base_dir: Path) -> Path:
    """Locate java binary within extracted JDK directory."""
    for root, dirs, files in os.walk(base_dir):
        if "java.exe" in files:
            return Path(root).parent
    return None


def find_neo4j_home(base_dir: Path) -> Path:
    """Locate neo4j directory containing bin/neo4j.bat."""
    for root, dirs, files in os.walk(base_dir):
        if "neo4j.bat" in files or "neo4j" in files:
            return Path(root).parent
    return None


def setup_and_start_neo4j():
    if is_port_open("localhost", BOLT_PORT):
        print(f"[Neo4j Setup] Neo4j is already listening on bolt://localhost:{BOLT_PORT} (HTTP: http://localhost:{HTTP_PORT})")
        return True

    LOCAL_DIR.mkdir(parents=True, exist_ok=True)

    jdk_dir = LOCAL_DIR / "jdk21"
    neo4j_dir = LOCAL_DIR / "neo4j"

    # 1. Setup JDK 21
    java_home = find_java_home(jdk_dir) if jdk_dir.exists() else None
    if not java_home:
        jdk_zip = LOCAL_DIR / "jdk21.zip"
        if not jdk_zip.exists():
            download_with_progress(JDK_ZIP_URL, jdk_zip)
        extract_zip(jdk_zip, jdk_dir)
        java_home = find_java_home(jdk_dir)
        if jdk_zip.exists():
            try:
                jdk_zip.unlink()
            except Exception:
                pass

    if not java_home:
        print("[Neo4j Setup] Error: Could not locate java.exe in extracted JDK.")
        return False
    print(f"[Neo4j Setup] Verified Java Home: {java_home}")

    # 2. Setup Neo4j Community Server
    neo4j_home = find_neo4j_home(neo4j_dir) if neo4j_dir.exists() else None
    if not neo4j_home:
        neo4j_zip = LOCAL_DIR / "neo4j.zip"
        if not neo4j_zip.exists():
            download_with_progress(NEO4J_ZIP_URL, neo4j_zip)
        extract_zip(neo4j_zip, neo4j_dir)
        neo4j_home = find_neo4j_home(neo4j_dir)
        if neo4j_zip.exists():
            try:
                neo4j_zip.unlink()
            except Exception:
                pass

    if not neo4j_home:
        print("[Neo4j Setup] Error: Could not locate neo4j home directory.")
        return False
    print(f"[Neo4j Setup] Verified Neo4j Home: {neo4j_home}")

    # 3. Configure initial password
    env = os.environ.copy()
    env["JAVA_HOME"] = str(java_home)
    env["PATH"] = f"{java_home / 'bin'};{env.get('PATH', '')}"
    env["NEO4J_HOME"] = str(neo4j_home)

    neo4j_admin = neo4j_home / "bin" / "neo4j-admin.bat"
    if neo4j_admin.exists():
        try:
            cmd = [str(neo4j_admin), "dbms", "set-initial-password", "password"]
            res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=15)
            print(f"[Neo4j Setup] Initial password configuration: {res.stdout.strip() or res.stderr.strip() or 'OK'}")
        except Exception as e:
            print(f"[Neo4j Setup] Password note: {e}")

    # 4. Start Neo4j server
    neo4j_bat = neo4j_home / "bin" / "neo4j.bat"
    print(f"[Neo4j Setup] Starting Neo4j server ({neo4j_bat})...")
    log_file = LOCAL_DIR / "neo4j_console.log"
    out = open(log_file, "w")
    proc = subprocess.Popen([str(neo4j_bat), "console"], env=env, stdout=out, stderr=subprocess.STDOUT)
    print(f"[Neo4j Setup] Server process started with PID: {proc.pid}. Waiting for Bolt port {BOLT_PORT}...")

    for i in range(45):
        if is_port_open("localhost", BOLT_PORT):
            print(f"[Neo4j Setup] SUCCESS: Neo4j is now live and accepting connections!")
            print(f"  Bolt Protocol: bolt://localhost:{BOLT_PORT}")
            print(f"  Neo4j Browser: http://localhost:{HTTP_PORT}")
            return True
        if proc.poll() is not None:
            print(f"[Neo4j Setup] Error: Neo4j process exited with code {proc.returncode}.")
            if log_file.exists():
                print("Neo4j log:")
                print(log_file.read_text()[-1000:])
            return False
        time.sleep(1)

    print("[Neo4j Setup] Warning: Timed out waiting for Neo4j port 7687.")
    return False


if __name__ == "__main__":
    success = setup_and_start_neo4j()
    sys.exit(0 if success else 1)
