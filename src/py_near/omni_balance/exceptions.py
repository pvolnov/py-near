"""Exceptions for omni_balance operations."""


class SimulationError(Exception):
    """Exception raised when intent simulation fails."""

    def __init__(self, message: str, error_data: dict = None):
        """
        Initialize simulation error.

        Args:
            message: Error message
            error_data: Optional error data dictionary
        """
        super().__init__(message)
        self.message = message
        self.error_data = error_data or dict()

