"""Design tokens mirrored from theme.qss for Python-side use
(colors in charts, drop shadows, dynamically-painted backgrounds, etc.)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Colors:
    # Surfaces
    bg: str = "#F8FAFC"
    card: str = "#FFFFFF"
    border: str = "#E5E7EB"
    border_strong: str = "#D1D5DB"
    hover: str = "#F9FAFB"

    # Text
    text: str = "#111827"
    text_muted: str = "#6B7280"
    text_subtle: str = "#9CA3AF"

    # Brand
    primary: str = "#6366F1"
    primary_hover: str = "#4F46E5"
    primary_pressed: str = "#4338CA"
    primary_soft: str = "#EEF2FF"

    # Status
    success: str = "#10B981"
    success_soft: str = "#ECFDF5"
    warning: str = "#F59E0B"
    warning_soft: str = "#FFFBEB"
    danger: str = "#EF4444"
    danger_soft: str = "#FEF2F2"
    info: str = "#3B82F6"


@dataclass(frozen=True)
class Spacing:
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48


@dataclass(frozen=True)
class Radius:
    sm: int = 8
    md: int = 10
    lg: int = 12
    xl: int = 14


COLORS = Colors()
SPACING = Spacing()
RADIUS = Radius()
