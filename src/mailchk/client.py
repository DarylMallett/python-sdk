"""Mailchk API client implementations."""

from typing import Sequence
import requests

from .models import ValidationResult, BulkValidationResult, UsageInfo
from .exceptions import (
    AuthenticationError,
    RateLimitError,
    ValidationError,
    APIError,
)


class Mailchk:
    """
    Synchronous client for the Mailchk email validation API.

    Example:
        >>> client = Mailchk("your-api-key")
        >>> result = client.validate("user@example.com")
        >>> if result.valid and not result.disposable:
        ...     print("Email is valid!")
    """

    BASE_URL = "https://api.mailchk.io/v1"
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the Mailchk client.

        Args:
            api_key: Your Mailchk API key
            base_url: Optional custom API base URL
            timeout: Request timeout in seconds (default: 30)
        """
        if not api_key:
            raise AuthenticationError("API key is required")

        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "mailchk-python/1.0.0",
            }
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict:
        """Make an HTTP request to the API."""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)

        try:
            response = self._session.request(method, url, **kwargs)
        except requests.RequestException as e:
            raise APIError(f"Request failed: {e}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> dict:
        """Handle API response and raise appropriate exceptions."""
        if response.status_code == 401:
            raise AuthenticationError()
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                retry_after=int(retry_after) if retry_after else None
            )
        elif response.status_code == 400:
            data = response.json()
            raise ValidationError(data.get("message", "Invalid request"))
        elif response.status_code >= 500:
            raise APIError(
                f"Server error: {response.status_code}",
                status_code=response.status_code,
            )
        elif not response.ok:
            raise APIError(
                f"API error: {response.status_code}",
                status_code=response.status_code,
            )

        return response.json()

    def validate(self, email: str) -> ValidationResult:
        """
        Validate a single email address.

        Args:
            email: The email address to validate

        Returns:
            ValidationResult with validation details

        Example:
            >>> result = client.validate("test@gmail.com")
            >>> print(f"Valid: {result.valid}, Risk: {result.risk}")
        """
        if not email or "@" not in email:
            raise ValidationError("Invalid email format")

        data = self._request("POST", "/validate", json={"email": email})
        return ValidationResult.from_dict(data)

    def validate_bulk(
        self,
        emails: Sequence[str],
    ) -> BulkValidationResult:
        """
        Validate multiple email addresses in a single request.

        Args:
            emails: List of email addresses to validate (max 100)

        Returns:
            BulkValidationResult with all validation results

        Example:
            >>> emails = ["user1@gmail.com", "user2@tempmail.com"]
            >>> result = client.validate_bulk(emails)
            >>> print(f"Valid: {result.valid}/{result.total}")
        """
        if not emails:
            raise ValidationError("At least one email is required")
        if len(emails) > 100:
            raise ValidationError("Maximum 100 emails per request")

        data = self._request("POST", "/validate/bulk", json={"emails": list(emails)})
        return BulkValidationResult.from_dict(data)

    def is_disposable(self, email: str) -> bool:
        """
        Quick check if an email is from a disposable provider.

        Args:
            email: The email address to check

        Returns:
            True if the email is disposable, False otherwise
        """
        result = self.validate(email)
        return result.disposable

    def is_valid(self, email: str) -> bool:
        """
        Quick check if an email is valid.

        Args:
            email: The email address to check

        Returns:
            True if the email is valid, False otherwise
        """
        result = self.validate(email)
        return result.valid

    def get_risk_score(self, email: str) -> int:
        """
        Get the risk score for an email address.

        Args:
            email: The email address to check

        Returns:
            Risk score from 0 (safe) to 100 (high risk)
        """
        result = self.validate(email)
        return result.risk_score

    def check_mx(self, domain: str) -> bool:
        """
        Check if a domain has valid MX records.

        Args:
            domain: The domain to check

        Returns:
            True if MX records exist, False otherwise
        """
        data = self._request("GET", f"/mx/{domain}")
        return data.get("valid", False)

    def get_usage(self) -> UsageInfo:
        """
        Get current API usage information.

        Returns:
            UsageInfo with quota details
        """
        data = self._request("GET", "/usage")
        return UsageInfo.from_dict(data)

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "Mailchk":
        return self

    def __exit__(self, *args) -> None:
        self.close()


class AsyncMailchk:
    """
    Asynchronous client for the Mailchk email validation API.

    Requires the 'async' extra: pip install mailchk[async]

    Example:
        >>> async with AsyncMailchk("your-api-key") as client:
        ...     result = await client.validate("user@example.com")
        ...     print(result.valid)
    """

    BASE_URL = "https://api.mailchk.io/v1"
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the async Mailchk client.

        Args:
            api_key: Your Mailchk API key
            base_url: Optional custom API base URL
            timeout: Request timeout in seconds (default: 30)
        """
        try:
            import aiohttp
        except ImportError:
            raise ImportError(
                "aiohttp is required for async support. "
                "Install with: pip install mailchk[async]"
            )

        if not api_key:
            raise AuthenticationError("API key is required")

        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: "aiohttp.ClientSession | None" = None

    async def _get_session(self) -> "aiohttp.ClientSession":
        """Get or create the aiohttp session."""
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "mailchk-python/1.0.0",
                },
            )
        return self._session

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict:
        """Make an async HTTP request to the API."""
        import aiohttp

        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with session.request(method, url, **kwargs) as response:
                return await self._handle_response(response)
        except aiohttp.ClientError as e:
            raise APIError(f"Request failed: {e}")

    async def _handle_response(self, response) -> dict:
        """Handle API response and raise appropriate exceptions."""
        if response.status == 401:
            raise AuthenticationError()
        elif response.status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                retry_after=int(retry_after) if retry_after else None
            )
        elif response.status == 400:
            data = await response.json()
            raise ValidationError(data.get("message", "Invalid request"))
        elif response.status >= 500:
            raise APIError(
                f"Server error: {response.status}",
                status_code=response.status,
            )
        elif response.status >= 400:
            raise APIError(
                f"API error: {response.status}",
                status_code=response.status,
            )

        return await response.json()

    async def validate(self, email: str) -> ValidationResult:
        """Validate a single email address asynchronously."""
        if not email or "@" not in email:
            raise ValidationError("Invalid email format")

        data = await self._request("POST", "/validate", json={"email": email})
        return ValidationResult.from_dict(data)

    async def validate_bulk(
        self,
        emails: Sequence[str],
    ) -> BulkValidationResult:
        """Validate multiple email addresses asynchronously."""
        if not emails:
            raise ValidationError("At least one email is required")
        if len(emails) > 100:
            raise ValidationError("Maximum 100 emails per request")

        data = await self._request(
            "POST", "/validate/bulk", json={"emails": list(emails)}
        )
        return BulkValidationResult.from_dict(data)

    async def is_disposable(self, email: str) -> bool:
        """Quick async check if an email is from a disposable provider."""
        result = await self.validate(email)
        return result.disposable

    async def is_valid(self, email: str) -> bool:
        """Quick async check if an email is valid."""
        result = await self.validate(email)
        return result.valid

    async def get_usage(self) -> UsageInfo:
        """Get current API usage information asynchronously."""
        data = await self._request("GET", "/usage")
        return UsageInfo.from_dict(data)

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> "AsyncMailchk":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
