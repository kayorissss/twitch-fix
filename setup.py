"""Setuptools configuration for TwitchFix.

Установка для разработчика:  pip install -e ".[dev]"
Запуск после установки:     twitchfix   (gui_scripts entry point)
Сборка .exe:                python build.py   (или build.bat в Windows)
"""
from __future__ import annotations

from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).parent

setup(
    name="twitchfix",
    version="1.0.0",
    description="Desktop diagnostics and repair utility for Twitch connectivity problems",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/kayorissss/twitch-fix",
    license="MIT",
    python_requires=">=3.11",
    # Пакет называется src (все импорты вида `from src.core ...`), поэтому
    # ищем пакеты от корня репозитория, а не внутри src/.
    packages=find_packages(include=["src", "src.*"]),
    include_package_data=True,
    package_data={"src": ["ui/styles/*.qss"]},
    data_files=[
        ("assets", [
            "assets/icon.png", "assets/icon.ico", "assets/logo.svg",
            "assets/banner.svg", "assets/banner.png",
        ]),
    ],
    install_requires=[
        "PyQt6>=6.6,<6.10",
        "requests>=2.31,<3",
        "dnspython>=2.4,<3",
        "psutil>=5.9,<8",
    ],
    extras_require={
        "dev": ["pytest>=8", "Pillow>=10", "ruff>=0.5"],
        "build": ["pyinstaller>=6.3,<7", "Pillow>=10"],
    },
    entry_points={"gui_scripts": ["twitchfix=src.main:run"]},
    classifiers=[
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: Microsoft :: Windows :: Windows 11",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Networking :: Monitoring",
    ],
)
