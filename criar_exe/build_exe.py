#!/usr/bin/env python3
"""Build standalone EXE for RelatoriosEncomendasEDI.

Cria distribuição Windows com FastAPI + Dashboard.

Uso:
    python build_exe.py                  # Build onedir (padrão)
    python build_exe.py --onefile        # Single-file EXE
    python build_exe.py --clean          # Limpar antes de build
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BuildConfig:
    """Configuração de build para RelatoriosEncomendasEDI."""

    BUILDER_DIR: Path = Path(__file__).resolve().parent
    PROJECT_ROOT: Path = BUILDER_DIR.parent
    ENTRYPOINT: Path = PROJECT_ROOT / "start_api.py"
    ICON_PATH: Path = BUILDER_DIR / "icon.ico"

    RELEASE_DIR: Path = BUILDER_DIR / "release"
    BUILD_DIR: Path = BUILDER_DIR / "build"
    SPEC_DIR: Path = BUILDER_DIR / "build_specs"
    DIST_FOLDER_NAME: str = "RelatoriosEncomendasEDI"

    APP_NAME: str = "RelatoriosEncomendasEDI"
    PRODUCT_NAME: str = "Relatórios Encomendas EDI"
    PRODUCT_VERSION: str = "1.0.0"
    FILE_VERSION: str = "1.0.0.0"
    COMPANY_NAME: str = "TIC SOL"
    AUTHOR_NAME: str = "TIC SOL"
    APP_DESCRIPTION: str = "Sistema integração EDI com FTP/SFTP e Generix Mailbox"
    LEGAL_COPYRIGHT: str = "Copyright (C) 2026 TIC SOL. Todos os direitos reservados."

    def __post_init__(self) -> None:
        if not self.PROJECT_ROOT.is_dir():
            raise FileNotFoundError(f"PROJECT_ROOT não encontrado: {self.PROJECT_ROOT}")
        if not self.ENTRYPOINT.exists():
            raise FileNotFoundError(f"Entrypoint não encontrado: {self.ENTRYPOINT}")


CONFIG = BuildConfig()


def main() -> int:
    """Build principal."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onefile", action="store_true", help="Single-file EXE")
    parser.add_argument("--clean", action="store_true", help="Limpar antes de build")
    parser.add_argument("--verbose", action="store_true", help="Debug output")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.clean:
        print("[BUILD] Limpando builds anteriores...")
        for d in [CONFIG.BUILD_DIR, CONFIG.SPEC_DIR]:
            if d.exists():
                shutil.rmtree(d)

    one_mode = "--onefile" if args.onefile else "--onedir"
    dist_dir = CONFIG.RELEASE_DIR / CONFIG.DIST_FOLDER_NAME

    print(f"[BUILD] Compilando {one_mode}...")
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        one_mode,
        "--name",
        CONFIG.APP_NAME,
        "--distpath",
        str(CONFIG.RELEASE_DIR),
        "--workpath",
        str(CONFIG.BUILD_DIR),
        "--specpath",
        str(CONFIG.SPEC_DIR),
        "--paths",
        str(CONFIG.PROJECT_ROOT / "src"),
        "--add-data",
        f"{CONFIG.PROJECT_ROOT / 'src' / 'integration_app' / 'api' / 'static'}{os.pathsep}integration_app/api/static",
        "--hidden-import=integration_app.api",
        "--hidden-import=integration_app.core",
        "--hidden-import=integration_app.storage",
        "--hidden-import=integration_app.transfers",
        "--hidden-import=apscheduler.schedulers.background",
        str(CONFIG.ENTRYPOINT),
    ]

    if CONFIG.ICON_PATH.exists():
        command.insert(command.index("--hidden-import=apscheduler.schedulers.background"), "--icon")
        command.insert(command.index("--hidden-import=apscheduler.schedulers.background") + 1, str(CONFIG.ICON_PATH))

    try:
        subprocess.run(command, check=True, cwd=CONFIG.PROJECT_ROOT)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Build falhou: {e}")
        return 1

    # Criar pastas de dados
    print("[BUILD] Preparando estrutura de produção...")
    (dist_dir / "data").mkdir(exist_ok=True)
    (dist_dir / "logs").mkdir(exist_ok=True)
    (dist_dir / "reports").mkdir(exist_ok=True)

    # Copiar config.example.yaml
    example_config = CONFIG.PROJECT_ROOT / "config.example.yaml"
    if example_config.exists():
        shutil.copy2(example_config, dist_dir / "config.example.yaml")

    # Copiar scripts batch
    for script in ["install_service.bat", "uninstall_service.bat", "README_PRODUCAO.txt"]:
        src = CONFIG.BUILDER_DIR / script
        if src.exists():
            shutil.copy2(src, dist_dir / script)

    print(f"[BUILD] ✓ Concluído: {dist_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
