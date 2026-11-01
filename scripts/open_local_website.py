"""Run the actual Masr Guide AI application on the user's Windows PC.

No public URL is created. Fail closed: the browser only opens if FastAPI is
ready, Vite has built successfully and the HTTP responses identify this app.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
LOG_DIR = ROOT / ".local-logs"
VENV_PYTHON = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
SITE = "http://127.0.0.1:5173/"
API = "http://127.0.0.1:8000/api/ready"
# Deliberately bypass machine/company proxies for loopback probes.
LOCAL_HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def run_checked(args: list[str], *, cwd: Path = ROOT, logfile: Path | None = None) -> None:
    print("\n[RUN] " + " ".join(args), flush=True)
    if logfile:
        LOG_DIR.mkdir(exist_ok=True)
        with logfile.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(args, cwd=str(cwd), stdout=output, stderr=subprocess.STDOUT)
            started = time.monotonic()
            while process.poll() is None:
                elapsed = int(time.monotonic() - started)
                print(f"[WORKING] {logfile.name} - {elapsed}s. Logs: {logfile}", flush=True)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    pass
                if time.monotonic() - started > 600 and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise RuntimeError(f"Setup/build exceeded 10 minutes. Check {logfile} and network access.")
            returncode = process.returncode
        if returncode:
            print(f"[FAILED] Command exited {returncode}; see {logfile}", flush=True)
            print(log_tail(logfile), flush=True)
    else:
        returncode = subprocess.run(args, cwd=str(cwd), check=False).returncode
    if returncode:
        raise RuntimeError("A setup/build command failed. Do NOT open the localhost link yet.")


def npm_command(*args: str) -> list[str]:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError("npm not found. Install Node.js 22 LTS from nodejs.org, restart your PC, and retry.")
    # Call npm.cmd through cmd explicitly on Windows; avoids .cmd invocation ambiguity.
    if os.name == "nt":
        return [os.environ.get("ComSpec", "cmd.exe"), "/d", "/c", npm, *args]
    return [npm, *args]


def fetch(url: str) -> tuple[int, str] | None:
    try:
        with LOCAL_HTTP.open(url, timeout=3) as response:
            return response.status, response.read(5000).decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return None


def healthy_backend(response: tuple[int, str] | None) -> bool:
    if not response or response[0] != 200:
        return False
    try:
        return json.loads(response[1]).get("status") == "ready"
    except (ValueError, AttributeError):
        return False


def healthy_frontend(response: tuple[int, str] | None) -> bool:
    if not response or response[0] != 200:
        return False
    text = response[1]
    return ("Masr Guide AI" in text and ('id="root"' in text or "id='root'" in text)
            and "/src/main.jsx" in text)


def log_tail(path: Path, n: int = 30) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except OSError:
        return "(No log available)"


def setup() -> None:
    print("[CHECK] Python 3.11+, Node.js 20+ and npm", flush=True)
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required. Use Python 3.12 if possible.")
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js missing. Install Node.js 22 LTS and restart the terminal.")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    print("[OK] Node " + version + " | Python " + sys.version.split()[0], flush=True)
    try:
        if int(version.lstrip("v").split(".")[0]) < 20:
            raise RuntimeError("Node.js 20+ is required. Install Node.js 22 LTS.")
    except ValueError as exc:
        raise RuntimeError("Cannot determine Node.js version: " + version) from exc
    run_checked(npm_command("--version"))

    if not VENV_PYTHON.is_file():
        print("[SETUP] Creating backend Python environment", flush=True)
        run_checked([sys.executable, "-m", "venv", str(BACKEND / ".venv")], logfile=LOG_DIR / "python-venv.log")
    check = subprocess.run([str(VENV_PYTHON), "-c", "import fastapi, uvicorn, dotenv, pydantic"],
                           capture_output=True, check=False)
    if check.returncode:
        print("[SETUP] Installing backend libraries", flush=True)
        run_checked([str(VENV_PYTHON), "-m", "pip", "install", "-r", "requirements.txt"],
                    cwd=BACKEND, logfile=LOG_DIR / "pip-install.log")

    vite = FRONTEND / "node_modules" / ".bin" / ("vite.cmd" if os.name == "nt" else "vite")
    if not vite.is_file():
        print("[SETUP] Installing complete React dependencies (internet required once)", flush=True)
        print("[SETUP] If this fails, read .local-logs/npm-install.log", flush=True)
        run_checked(npm_command("ci", "--include=dev", "--no-audit", "--no-fund", "--fetch-retries=1"),
                    cwd=FRONTEND, logfile=LOG_DIR / "npm-install.log")
    if not vite.is_file():
        raise RuntimeError("Vite is missing after npm install; see .local-logs/npm-install.log")

    print("[CHECK] Building the real React application", flush=True)
    run_checked(npm_command("run", "build"), cwd=FRONTEND,
                logfile=LOG_DIR / "frontend-build.log")
    print("[OK] React production build succeeded", flush=True)


def main() -> int:
    print("\n======================================================\n"
          " MASR GUIDE AI - LOCAL WEBSITE LAUNCHER\n"
          "======================================================", flush=True)
    print("This starts the app on YOUR PC only. It does not publish a public URL.", flush=True)
    LOG_DIR.mkdir(exist_ok=True)
    setup()

    # Refuse to reuse unknown/stale local servers from previously downloaded ZIPs.
    if fetch(API) is not None or fetch(SITE) is not None:
        raise RuntimeError("Port 8000 or 5173 already has a running app. Close old FastAPI/Vite windows "
                           "and run this launcher again. Don't test an older copy by mistake.")

    streams: list[object] = []
    processes: list[subprocess.Popen] = []
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    try:
        backend_log = (LOG_DIR / "backend.log").open("w", encoding="utf-8")
        streams.append(backend_log)
        processes.append(subprocess.Popen(
            [str(VENV_PYTHON), "-m", "uvicorn", "app.main:app", "--no-proxy-headers", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(BACKEND), stdout=backend_log, stderr=subprocess.STDOUT, creationflags=flags))
        print("[START] FastAPI backend on port 8000", flush=True)

        frontend_log = (LOG_DIR / "frontend.log").open("w", encoding="utf-8")
        streams.append(frontend_log)
        processes.append(subprocess.Popen(
            npm_command("run", "dev", "--", "--host", "127.0.0.1", "--strictPort"),
            cwd=str(FRONTEND), stdout=frontend_log, stderr=subprocess.STDOUT, creationflags=flags))
        print("[START] Vite frontend on port 5173", flush=True)

        print("[CHECK] Waiting for both FastAPI and React (up to 60 seconds)", flush=True)
        ready = False
        for _ in range(60):
            if any(proc.poll() is not None for proc in processes):
                break
            if healthy_backend(fetch(API)) and healthy_frontend(fetch(SITE)):
                ready = True
                break
            time.sleep(1)
        if not ready:
            print("[FAILED] React or FastAPI did not become ready. Last log lines:", flush=True)
            for name in ("backend.log", "frontend.log"):
                path = LOG_DIR / name
                print(f"\n--- {name} ---\n{log_tail(path)}", flush=True)
            return 1

        print("\n[READY] React AND FastAPI both responded with expected content.", flush=True)
        print("[READY] Open in regular Chrome or Edge on THIS SAME Windows PC:", flush=True)
        print("         " + SITE, flush=True)
        print("         API: " + API, flush=True)
        print("Do not open localhost in a remote/in-app browser.\n", flush=True)
        webbrowser.open(SITE)
        print("Keep this console open. Ctrl+C stops the two services.", flush=True)
        while all(proc.poll() is None for proc in processes):
            time.sleep(1)
        print("[FAILED] One local service stopped. See .local-logs", flush=True)
        for name in ("backend.log", "frontend.log"):
            print(f"\n--- {name} ---\n{log_tail(LOG_DIR / name)}", flush=True)
        return 1
    except KeyboardInterrupt:
        print("[STOP] Stopping local services", flush=True)
        return 0
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        for stream in streams:
            stream.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print("\n[FAILED] " + str(error), flush=True)
        print("Check logs in .local-logs; do NOT claim the local website is running.", flush=True)
        sys.exit(1)
