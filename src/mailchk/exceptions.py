"""Mailchk SDK exceptions."""


class MailchkError(Exception):
    """Base exception for all Mailchk errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(MailchkError):
    """Raised when API key is invalid or missing."""

    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(message, status_code=401)


class RateLimitError(MailchkError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ValidationError(MailchkError):
    """Raised when validation request is invalid."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class APIError(MailchkError):
    """Raised when API returns an unexpected error."""

    pass
