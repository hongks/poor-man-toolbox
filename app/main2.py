from textual.app import App, ComposeResult
from textual.widgets import Placeholder

from ui.body import _body
from ui.footer import _footer
from ui.header import _header


class PoorManToolboxApp(App):
    # set up the theme and styling
    CSS_PATH = None
    THEME = "dracula"
    THEMES = [
        "catppuccin-mocha",
        "dracula",
        "gruvbox",
        "nord",
        "tokyo-night",
        "textual-dark",
        "textual-light",
    ]

    # heading
    TITLE = "poor-man-toolbox"
    SUB_TITLE = "dashboard"

    # ...
    BINDINGS = [
        ("m", "toggle_theme", "toggle theme"),
        ("q", "quit", "quit"),
        ("h", "help", "help"),
    ]

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        yield _header()
        yield Placeholder("this is a test")
        yield _footer()

    def on_mount(self):
        pass

    def action_toggle_theme(self):
        idx = self.THEMES.index(self.theme)
        self.theme = self.THEMES[(idx + 1) % len(self.THEMES)]


if __name__ == "__main__":
    PoorManToolboxApp().run()
