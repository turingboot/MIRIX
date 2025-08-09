#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable  # current interpreter

MAIN_SPEC = REPO_ROOT / "main.spec"
REQUIREMENTS = REPO_ROOT / "requirements.txt"
DIST_DIR = REPO_ROOT / "dist"


def run(cmd, cwd=None, env=None):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ensure_pip():
    try:
        run([PYTHON, "-m", "pip", "--version"]) 
    except SystemExit:
        print("pip not found for current interpreter")
        raise


def pip_install(args):
    run([PYTHON, "-m", "pip", "install", "--upgrade"] + args)


def ensure_dependencies():
    ensure_pip()

    # Ensure wheel for faster/safer installs
    pip_install(["pip", "setuptools", "wheel"])

    # Install project dependencies (for PyInstaller analysis hooks)
    if REQUIREMENTS.exists():
        print(f"Installing requirements from {REQUIREMENTS}")
        run([PYTHON, "-m", "pip", "install", "-r", str(REQUIREMENTS)])

    # Ensure pyinstaller
    pip_install(["pyinstaller"])  # version can be pinned if needed


def build_with_pyinstaller(clean=True):
    if not MAIN_SPEC.exists():
        print(f"Error: spec not found: {MAIN_SPEC}")
        raise SystemExit(1)

    cmd = [PYTHON, "-m", "PyInstaller", str(MAIN_SPEC)]
    if clean:
        cmd.append("--clean")

    # Make sure dist exists/clean it if requested
    if clean and DIST_DIR.exists():
        print(f"Cleaning dist directory: {DIST_DIR}")
        shutil.rmtree(DIST_DIR)

    run(cmd, cwd=str(REPO_ROOT))


def normalize_output_names():
    system = platform.system().lower()
    if system == "windows":
        exe_path = DIST_DIR / "main.exe"
        no_ext_path = DIST_DIR / "main"
        if exe_path.exists():
            # Duplicate .exe to 'main' to keep frontend copy script compatible
            try:
                shutil.copy2(exe_path, no_ext_path)
                print(f"Created Windows-compatible copy: {no_ext_path} (duplicate of main.exe)")
            except Exception as e:
                print(f"Warning: failed to duplicate main.exe to main: {e}")
        else:
            print("Error: dist/main.exe not found after build")
            raise SystemExit(1)
    else:
        # On Unix-like systems we expect 'dist/main'
        unix_path = DIST_DIR / "main"
        if not unix_path.exists():
            # Some configurations might output inside a folder; try to locate
            candidates = list(DIST_DIR.glob("main*"))
            if candidates:
                print(f"Note: expected 'dist/main' not found, candidates: {[str(p) for p in candidates]}")
            print("Error: dist/main not found after build")
            raise SystemExit(1)
        # Ensure executable bit
        try:
            mode = os.stat(unix_path).st_mode
            os.chmod(unix_path, mode | 0o755)
        except Exception as e:
            print(f"Warning: failed to chmod +x on {unix_path}: {e}")


def print_artifact_info():
    system = platform.system().lower()
    artifact = DIST_DIR / ("main.exe" if system == "windows" else "main")
    if not artifact.exists():
        # On Windows we also wrote a duplicate without extension; try it
        fallback = DIST_DIR / "main"
        artifact = artifact if artifact.exists() else fallback

    if artifact.exists():
        size_mb = artifact.stat().st_size / (1024 * 1024)
        print(f"\n✅ Build success: {artifact} ({size_mb:.2f} MB)")
    else:
        print("\n❌ Build finished but artifact not found")


def main():
    print("Building MIRIX backend executable with PyInstaller…")
    print(f"Python: {PYTHON}")
    print(f"Repo root: {REPO_ROOT}")

    ensure_dependencies()
    build_with_pyinstaller(clean=True)
    normalize_output_names()
    print_artifact_info()

    print("\nNotes:")
    print("- Cross-platform builds require running this script on each target OS (Windows/macOS/Linux).")
    print("- For Linux reproducible builds, consider running on a compatible glibc distro or use a Docker image.")
    print("- UPX (executable packer) can be installed separately if you want smaller binaries.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)
