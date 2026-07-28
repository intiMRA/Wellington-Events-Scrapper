from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"


def root_path(name: str) -> str:
    return str(ROOT / name)


def data_path(name: str) -> str:
    return str(DATA_DIR / name)


def model_path(name: str) -> str:
    return str(MODELS_DIR / name)
