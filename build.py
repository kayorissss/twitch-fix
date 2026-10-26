"""Сборка одного .exe через PyInstaller (Windows 10/11, без консоли).

    python build.py            # обычная сборка
    python build.py --debug    # сборка с консолью для отладки

Итог: dist/TwitchFix.exe. Все ресурсы (иконки, QSS) упакованы внутрь.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEP = os.pathsep  # ';' на Windows, ':' на Linux/macOS

# Qt-модули, которые не используются приложением. Исключение заметно
# уменьшает размер onefile-архива.
EXCLUDES = [
    "tkinter", "matplotlib", "numpy", "PIL", "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore", "PyQt6.Qt3DCore", "PyQt6.Qt3DRender",
    "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets", "PyQt6.QtQuick",
    "PyQt6.QtQml", "PyQt6.QtCharts", "PyQt6.QtDataVisualization",
    "PyQt6.QtBluetooth", "PyQt6.QtNfc", "PyQt6.QtPositioning",
    "PyQt6.QtSerialPort", "PyQt6.QtSql", "PyQt6.QtTest", "PyQt6.QtDesigner",
]
HIDDEN_IMPORTS = ["dns.resolver", "dns.rdatatype", "dns.exception", "psutil", "requests"]


def ensure_icons() -> None:
    """Создать icon.ico, если его нет (Pillow — зависимость только для сборки)."""
    icon = ROOT / "assets" / "icon.ico"
    if icon.exists():
        return
    try:
        sys.path.insert(0, str(ROOT))
        from scripts.generate_assets import write_icons  # noqa: PLC0415

        write_icons()
    except Exception as exc:
        print(f"[warn] cannot generate icon: {exc}")


def build(debug: bool = False, upx_dir: str | None = None) -> int:
    ensure_icons()
    command: list[str] = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile",
        "--windowed" if not debug else "--console",
        "--name", "TwitchFix",
        "--icon", str(ROOT / "assets" / "icon.ico"),
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT),
        "--log-level", "WARN",
        "--add-data", f"{ROOT / 'assets'}{SEP}assets",
        "--add-data", f"{ROOT / 'src' / 'ui' / 'styles'}{SEP}src/ui/styles",
    ]
    for module in EXCLUDES:
        command += ["--exclude-module", module]
    for module in HIDDEN_IMPORTS:
        command += ["--hidden-import", module]
    # dnspython импортирует типы RDATA динамически — забираем все подмодули.
    command += ["--collect-submodules", "dns"]
    if upx_dir:
        command += ["--upx-dir", upx_dir]
    elif os.environ.get("UPX_DIR"):
        command += ["--upx-dir", os.environ["UPX_DIR"]]
    command.append(str(ROOT / "src" / "main.py"))

    print("PyInstaller command:\n  " + " ".join(command) + "\n")
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode == 0:
        executable = ROOT / "dist" / ("TwitchFix.exe" if os.name == "nt" else "TwitchFix")
        print(f"\nDone: {executable}")
        if executable.exists():
            print(f"Size: {executable.stat().st_size / 1024 / 1024:.1f} MB")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Build TwitchFix one-file executable")
    parser.add_argument("--debug", action="store_true", help="keep the console window")
    parser.add_argument("--upx-dir", default=None, help="path to UPX binaries to shrink the exe")
    args = parser.parse_args()
    try:
        import PyInstaller  # noqa: F401,PLC0415
    except ImportError:
        print("PyInstaller is not installed. Run: pip install pyinstaller")
        return 1
    return build(debug=args.debug, upx_dir=args.upx_dir)


if __name__ == "__main__":
    raise SystemExit(main())
