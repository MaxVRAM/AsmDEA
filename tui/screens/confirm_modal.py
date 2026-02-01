"""Confirmation modal dialog for user actions.

Simple modal screen with message and Confirm/Cancel buttons.
"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmModal(ModalScreen[bool]):
    """Modal dialog for confirmation prompts.

    Returns True if confirmed, False if cancelled.
    """

    CSS = """
    ConfirmModal {
        align: center middle;
    }

    #modal-container {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }

    #message {
        text-align: center;
        margin-bottom: 2;
    }

    #button-container {
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 2;
    }
    """

    def __init__(self, message: str) -> None:
        """Initialize the confirmation modal.

        Args:
            message: Message to display
        """
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="modal-container"):
            yield Label(self.message, id="message")
            with Vertical(id="button-container"):
                yield Button("Confirm", id="confirm-button", variant="primary")
                yield Button("Cancel", id="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button press event
        """
        if event.button.id == "confirm-button":
            self.dismiss(True)
        else:
            self.dismiss(False)
