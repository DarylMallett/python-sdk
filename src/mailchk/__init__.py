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
from .models import ValidationResult, BulkValidationResult, UsageInfo, MxRecord
from .exceptions import (
    MailchkError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    APIError,
)
from .config import from_environment, get_client, configure

__version__ = "1.2.0"
__all__ = [
    "Mailchk",
    "AsyncMailchk",
    "ValidationResult",
    "BulkValidationResult",
    "UsageInfo",
    "MxRecord",
    "MailchkError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "APIError",
    "from_environment",
    "get_client",
    "configure"
]
