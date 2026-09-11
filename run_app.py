import os
import sys
import subprocess
import time
import webbrowser
import signal

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    print("=" * 60)
    print("🚀 Starting FQC Validator & Quality Control Dashboard...")
    print("=" * 60)

    # 1. Start Backend (Flask)
    print("[1/2] Starting Flask backend server on http://127.0.0.1:5000 ...")
    backend_cmd = [sys.executable, "app.py"]
    backend_process = subprocess.Popen(
        backend_cmd,
        cwd=backend_dir,
        shell=False
    )

    # 2. Start Frontend (Vite)
    print("[2/2] Starting Vite frontend server on http://localhost:5173 ...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_process = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=frontend_dir,
        shell=True if os.name == "nt" else False
    )

    # Give servers a moment to initialize
    time.sleep(2)
    url = "http://localhost:5173"
    print(f"\n✨ Application ready! Opening {url} in your browser...")
    webbrowser.open(url)
    print("\nPress Ctrl+C in this terminal to stop both servers.")
    print("=" * 60)

    def shutdown(signum, frame):
        print("\n🛑 Shutting down servers...")
        try:
            backend_process.terminate()
        except Exception:
            pass
        try:
            frontend_process.terminate()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            # Check if any process died unexpectedly
            if backend_process.poll() is not None:
                print(f"[!] Backend process stopped with code {backend_process.returncode}")
                break
            if frontend_process.poll() is not None:
                print(f"[!] Frontend process stopped with code {frontend_process.returncode}")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown(None, None)

if __name__ == "__main__":
    main()