from pathlib import Path

from PySide6.QtCore import QFile, QIODevice
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget


def load_ui(path: Path, parent: QWidget | None = None) -> QWidget:
    loader = QUiLoader()
    f = QFile(str(path))
    if not f.open(QIODevice.ReadOnly):
        raise RuntimeError(f"Cannot open UI file: {path}")
    w = loader.load(f, parent)
    f.close()
    if w is None:
        raise RuntimeError(f"Failed to load UI: {path}")
    return w
