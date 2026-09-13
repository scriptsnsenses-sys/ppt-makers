"""DGSL error type shared by every stage of the pipeline."""


class DGSLError(Exception):
    """A user-facing DGSL failure with an optional source line."""

    def __init__(self, message, line=None):
        self.line = line
        if line is not None and not message.startswith(f"line {line}:"):
            message = f"line {line}: {message}"
        super().__init__(message)
