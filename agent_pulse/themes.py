"""Color themes for Agent Pulse terminal rendering.

Each theme defines a palette of named colors used throughout the UI.
"""

from dataclasses import dataclass


@dataclass
class Theme:
    """Color palette for terminal rendering."""
    name: str

    # Primary colors
    primary: str        # Main accent (headers, highlights)
    secondary: str      # Secondary accent
    success: str        # Green/success indicators
    warning: str        # Yellow/warning
    danger: str         # Red/danger, cost
    info: str           # Blue/info

    # UI elements
    header: str         # Header text style
    border: str         # Panel/table borders
    dim: str            # Dim/muted text
    text: str           # Normal text
    highlight: str = ""  # Special highlights

    # Data colors (for charts, breakdowns)
    data_colors: tuple = (
        "blue", "magenta", "green", "yellow", "red",
        "cyan", "bright_blue", "bright_magenta",
    )

    # Source emojis with colors
    source_emojis: dict = None  # type: ignore

    def __post_init__(self):
        if self.source_emojis is None:
            self.source_emojis = {
                "cli": "💻",
                "cron": "⏰",
                "weixin": "💬",
                "web": "🌐",
            }
        if not self.highlight:
            self.highlight = self.primary


# ─── Built-in Themes ─────────────────────────────────────────────

DEFAULT = Theme(
    name="default",
    primary="bold cyan",
    secondary="magenta",
    success="bold green",
    warning="bold yellow",
    danger="bold red",
    info="blue",
    header="bold cyan",
    border="dim blue",
    dim="dim",
    text="",
)

DRACULA = Theme(
    name="dracula",
    primary="bold #bd93f9",     # Purple
    secondary="bold #ff79c6",   # Pink
    success="bold #50fa7b",     # Green
    warning="bold #f1fa8c",     # Yellow
    danger="bold #ff5555",      # Red
    info="bold #8be9fd",        # Cyan
    header="bold #bd93f9",
    border="dim #6272a4",       # Comment
    dim="dim #6272a4",
    text="#f8f8f2",
    data_colors=(
        "#bd93f9", "#ff79c6", "#50fa7b", "#f1fa8c",
        "#ff5555", "#8be9fd", "#ffb86c", "#6272a4",
    ),
)

MONOKAI = Theme(
    name="monokai",
    primary="bold #f92672",     # Pink/red
    secondary="bold #a6e22e",   # Green
    success="bold #a6e22e",
    warning="bold #e6db74",     # Yellow
    danger="bold #f92672",
    info="bold #66d9ef",        # Blue
    header="bold #f92672",
    border="dim #75715e",
    dim="dim #75715e",
    text="#f8f8f2",
    data_colors=(
        "#f92672", "#a6e22e", "#e6db74", "#66d9ef",
        "#ae81ff", "#fd971f", "#f8f8f2", "#75715e",
    ),
)

LIGHT = Theme(
    name="light",
    primary="bold blue",
    secondary="magenta",
    success="bold green",
    warning="bold dark_orange",
    danger="bold red",
    info="dark_blue",
    header="bold blue",
    border="dim grey50",
    dim="dim grey50",
    text="black",
    data_colors=(
        "blue", "magenta", "green", "dark_orange",
        "red", "cyan", "dark_violet", "grey50",
    ),
)


# ─── Theme registry ──────────────────────────────────────────────

THEMES: dict[str, Theme] = {
    "default": DEFAULT,
    "dracula": DRACULA,
    "monokai": MONOKAI,
    "light": LIGHT,
}


def get_theme(name: str) -> Theme:
    """Get theme by name, falling back to default."""
    return THEMES.get(name, DEFAULT)


def list_themes() -> list[str]:
    """List available theme names."""
    return list(THEMES.keys())
