"""NeuraScreen GUI — Desktop interface for scenario editing and video generation."""


def launch_gui(args: list[str] | None = None) -> None:
    """Launch the NeuraScreen GUI application.

    Args:
        args: Optional command-line arguments to pass to QApplication.
    """
    try:
        from .app import NeuraScreenApp
    except ImportError as e:
        raise RuntimeError(
            "PySide6 is required for the GUI. Install it with:\n"
            "  pip install neurascreen[gui]"
        ) from e

    app = NeuraScreenApp(args or [])
    app.run()
