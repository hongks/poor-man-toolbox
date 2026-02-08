from textual.widgets import Header


class _header(Header):
    def __init__(self) -> None:
        super().__init__(show_clock=True)
