from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resource_ui(name: str) -> Path:
    return project_root() / "resources" / "ui" / name


def resource_icon(name: str) -> Path:
    return project_root() / "resources" / "icons" / name


def data_dir() -> Path:
    d = project_root() / "jobhub_data"
    d.mkdir(parents=True, exist_ok=True)
    return d
