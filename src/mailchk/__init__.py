"""
Mailchk - Email Validation API SDK for Python

Official Python SDK for the Mailchk email validation API.
Validate emails, detect disposable addresses, and assess risk scores.

Example:
    >>> from mailchk import Mailchk
    >>> client = Mailchk("your-api-key")
    >>> result = client.validate("test@example.com")
    >>> print(result.valid)
    True
"""

from .client import Mailchk, AsyncMailchk
from .models import ValidationResult, BulkValidationResult, UsageInfo
from .exceptions import (
    MailchkError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    APIError,
)

__version__ = "1.0.0"
__all__ = [
    "Mailchk",
    "AsyncMailchk",
    "ValidationResult",
    "BulkValidationResult",
    "UsageInfo",
    "MailchkError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "APIError",
]
