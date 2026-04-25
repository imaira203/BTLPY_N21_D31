# Icon System

All icons are inline SVG (Lucide-style: 24x24 viewBox, 1.5 stroke, currentColor).
At runtime `app/components/icons.py` colors them and converts to QIcon via
`QSvgRenderer` → `QPixmap`. Keeping icons in one Python file avoids shipping
dozens of loose SVG files, and the `color` argument lets a single icon tint
to match whatever state it's in (muted / primary / danger).

If you prefer separate SVG files later, drop them here and change
`icons.py` to read from disk. The public API (`Icon.get("search", size, color)`)
stays the same.
