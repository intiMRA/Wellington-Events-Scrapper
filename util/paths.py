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


def scraper_dir(name: str) -> Path:
    return DATA_DIR / "scrapers" / name


def scraper_path(name: str, filename: str) -> str:
    return str(scraper_dir(name) / filename)
