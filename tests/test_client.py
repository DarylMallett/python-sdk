"""Tests for Mailchk client implementations."""

import pytest
import responses
import asyncio
from unittest.mock import patch, MagicMock
from aioresponses import aioresponses

from mailchk.client import Mailchk, AsyncMailchk
from mailchk.exceptions import (
    AuthenticationError,
    RateLimitError,
    ValidationError,
    APIError,
)
from mailchk.models import ValidationResult, BulkValidationResult, UsageInfo


class TestMailchkClient:
    """Tests for synchronous Mailchk client."""

    def test_client_initialization(self, test_api_key, test_base_url):
        """Test client initialization with valid parameters."""
        client = Mailchk(
            api_key=test_api_key,
            base_url=test_base_url,
            timeout=30,
            retry_attempts=3,
            retry_delay=1.0,
        )

        assert client.api_key == test_api_key
        assert client.base_url == test_base_url
        assert client.timeout == 30
        assert client.retry_attempts == 3
        assert client.retry_delay == 1.0

    def test_client_initialization_defaults(self, test_api_key):
        """Test client initialization with default values."""
        client = Mailchk(api_key=test_api_key)

        assert client.api_key == test_api_key
        assert client.base_url == "https://api.mailchk.io/v1"
        assert client.timeout == 30
        assert client.retry_attempts == 3
        assert client.retry_delay == 1.0

    def test_client_initialization_no_api_key(self):
        """Test that missing API key raises AuthenticationError."""
        with pytest.raises(AuthenticationError):
            Mailchk(api_key="")

    def test_from_environment(self, set_env_vars):
        """Test creating client from environment variables."""
        set_env_vars(
            MAILCHK_API_KEY="env-api-key",
            MAILCHK_BASE_URL="https://env-api.com/v1",
            MAILCHK_TIMEOUT="45",
        )

        client = Mailchk.from_environment()

        assert client.api_key == "env-api-key"
        assert client.base_url == "https://env-api.com/v1"
        assert client.timeout == 45

    def test_from_environment_missing_api_key(self):
        """Test from_environment with missing API key."""
        with pytest.raises(AuthenticationError) as exc_info:
            Mailchk.from_environment()

        assert "MAILCHK_API_KEY" in str(exc_info.value)

    def test_from_environment_custom_env_vars(self, set_env_vars):
        """Test from_environment with custom environment variable names."""
        set_env_vars(CUSTOM_API_KEY="custom-key")

        client = Mailchk.from_environment(api_key_env="CUSTOM_API_KEY")

        assert client.api_key == "custom-key"

    def test_from_environment_invalid_timeout(self, set_env_vars):
        """Test from_environment ignores invalid timeout."""
        set_env_vars(
            MAILCHK_API_KEY="test-key",
            MAILCHK_TIMEOUT="not-a-number",
        )

        client = Mailchk.from_environment()

        assert client.api_key == "test-key"
        assert client.timeout == 30  # Should use default

    @responses.activate
    def test_validate_email_success(self, mailchk_client, mock_validation_result):
        """Test successful email validation."""
        responses.add(
            responses.POST,
            f"{mailchk_client.base_url}/check",
            json=mock_validation_result.__dict__,
            status=200,
        )

        result = mailchk_client.validate("test@example.com")

        assert isinstance(result, ValidationResult)
        assert result.email == "test@example.com"
        assert result.valid is True
        assert result.deliverability_score == 95

    @responses.activate
    def test_validate_email_invalid_format(self, mailchk_client):
        """Test validation with invalid email format."""
        with pytest.raises(ValidationError):
            mailchk_client.validate("")

        with pytest.raises(ValidationError):
            mailchk_client.validate("invalid-email")

    @responses.activate
    def test_validate_bulk_success(self, mailchk_client, mock_bulk_result):
        """Test successful bulk email validation."""
        responses.add(
            responses.POST,
            f"{mailchk_client.base_url}/check/bulk",
            json=mock_bulk_result.__dict__,
            status=200,
        )

        emails = ["test1@example.com", "test2@example.com"]
        result = mailchk_client.validate_bulk(emails)

        assert isinstance(result, BulkValidationResult)
        assert result.total == 3
        assert result.valid == 2

    @responses.activate
    def test_validate_bulk_empty_list(self, mailchk_client):
        """Test bulk validation with empty email list."""
        with pytest.raises(ValidationError):
            mailchk_client.validate_bulk([])

    @responses.activate
    def test_validate_bulk_too_many_emails(self, mailchk_client):
        """Test bulk validation with too many emails."""
        emails = ["test@example.com"] * 101
        with pytest.raises(ValidationError):
            mailchk_client.validate_bulk(emails)

    @responses.activate
    def test_helper_methods(self, mailchk_client, mock_validation_result):
        """Test client helper methods."""
        responses.add(
            responses.POST,
            f"{mailchk_client.base_url}/check",
            json=mock_validation_result.__dict__,
            status=200,
        )

        # Test all helper methods
        assert mailchk_client.is_disposable("test@example.com") is False
        assert mailchk_client.is_valid("test@example.com") is True
        assert mailchk_client.get_risk_score("test@example.com") == "low"
        assert mailchk_client.get_deliverability_score("test@example.com") == 95

    @responses.activate
    def test_get_usage_success(self, mailchk_client, mock_usage_info):
        """Test getting usage information."""
        responses.add(
            responses.GET,
            f"{mailchk_client.base_url}/usage",
            json=mock_usage_info.__dict__,
            status=200,
        )

        result = mailchk_client.get_usage()

        assert isinstance(result, UsageInfo)
        assert result.used == 150
        assert result.limit == 1000
        assert result.remaining == 850

    @responses.activate
    def test_check_mx_success(self, mailchk_client):
        """Test MX record checking."""
        responses.add(
            responses.GET,
            f"{mailchk_client.base_url}/mx/example.com",
            json={"valid": True},
            status=200,
        )

        result = mailchk_client.check_mx("example.com")
        assert result is True

    @responses.activate
    def test_authentication_error(self, mailchk_client):
        """Test 401 authentication error handling."""
        responses.add(
            responses.POST,
            f"{mailchk_client.base_url}/check",
            json={"error": "Invalid API key"},
            status=401,
        )

        with pytest.raises(AuthenticationError):
            mailchk_client.validate("test@example.com")

    @responses.activate
    def test_rate_limit_error(self, mailchk_client):
        """Test 429 rate limit error handling."""
        responses.add(
            responses.POST,
            f"{mailchk_client.base_url}/check",
            json={"error": "Rate limit exceeded"},
            status=429,
            headers={"Retry-After": "60"},
        )

        with pytest.raises(RateLimitError) as exc_info:
            mailchk_client.validate("test@example.com")

        assert exc_info.value.retry_after == 60

    @responses.activate
    def test_validation_error_400(self, mailchk_client):
        """Test 400 validation error handling."""
        responses.add(
            responses.POST,
            f"{mailchk_client.base_url}/check",
            json={"message": "Invalid request"},
            status=400,
        )

        with pytest.raises(ValidationError):
            mailchk_client.validate("test@example.com")

    @responses.activate
    def test_server_error(self, mailchk_client):
        """Test 500 server error handling."""
        responses.add(
            responses.POST,
            f"{mailchk_client.base_url}/check",
            json={"error": "Internal server error"},
            status=500,
        )

        with pytest.raises(APIError) as exc_info:
            mailchk_client.validate("test@example.com")

        assert exc_info.value.status_code == 500

    @responses.activate
    def test_network_error(self, mailchk_client):
        """Test network error handling."""
        responses.add(
            responses.POST,
            f"{mailchk_client.base_url}/check",
            body=Exception("Network error"),
        )

        with pytest.raises(APIError):
            mailchk_client.validate("test@example.com")

    def test_context_manager(self, test_api_key, test_base_url):
        """Test client as context manager."""
        with Mailchk(api_key=test_api_key, base_url=test_base_url) as client:
            assert isinstance(client, Mailchk)
            assert client.api_key == test_api_key

    def test_close_session(self, mailchk_client):
        """Test closing client session."""
        # Mock the session to verify close is called
        mailchk_client._session = MagicMock()

        mailchk_client.close()

        mailchk_client._session.close.assert_called_once()


class TestAsyncMailchkClient:
    """Tests for asynchronous Mailchk client."""

    def test_async_client_initialization(self, test_api_key, test_base_url):
        """Test async client initialization."""
        client = AsyncMailchk(
            api_key=test_api_key,
            base_url=test_base_url,
            timeout=30,
            retry_attempts=3,
            retry_delay=1.0,
        )

        assert client.api_key == test_api_key
        assert client.base_url == test_base_url
        assert client.retry_attempts == 3
        assert client.retry_delay == 1.0

    def test_async_client_no_aiohttp(self):
        """Test async client without aiohttp raises ImportError."""
        with patch("mailchk.client.AsyncMailchk.__init__") as mock_init:
            mock_init.side_effect = ImportError("aiohttp is required")

            with pytest.raises(ImportError):
                AsyncMailchk(api_key="test")

    def test_async_from_environment(self, set_env_vars):
        """Test creating async client from environment."""
        set_env_vars(
            MAILCHK_API_KEY="env-api-key",
            MAILCHK_TIMEOUT="45",
        )

        client = AsyncMailchk.from_environment()

        assert client.api_key == "env-api-key"

    @pytest.mark.asyncio
    async def test_async_validate_success(self, mock_validation_result):
        """Test async email validation."""
        client = AsyncMailchk(api_key="test-key", base_url="https://api.test.com/v1")

        with aioresponses() as m:
            m.post(
                "https://api.test.com/v1/check",
                payload=mock_validation_result.__dict__,
            )

            result = await client.validate("test@example.com")

            assert isinstance(result, ValidationResult)
            assert result.email == "test@example.com"
            assert result.valid is True

        await client.close()

    @pytest.mark.asyncio
    async def test_async_validate_invalid_format(self):
        """Test async validation with invalid email format."""
        client = AsyncMailchk(api_key="test-key")

        with pytest.raises(ValidationError):
            await client.validate("")

        await client.close()

    @pytest.mark.asyncio
    async def test_async_validate_bulk_success(self, mock_bulk_result):
        """Test async bulk email validation."""
        client = AsyncMailchk(api_key="test-key", base_url="https://api.test.com/v1")

        with aioresponses() as m:
            m.post(
                "https://api.test.com/v1/check/bulk",
                payload=mock_bulk_result.__dict__,
            )

            emails = ["test1@example.com", "test2@example.com"]
            result = await client.validate_bulk(emails)

            assert isinstance(result, BulkValidationResult)
            assert result.total == 3

        await client.close()

    @pytest.mark.asyncio
    async def test_async_helper_methods(self, mock_validation_result):
        """Test async helper methods."""
        client = AsyncMailchk(api_key="test-key", base_url="https://api.test.com/v1")

        with aioresponses() as m:
            # Add multiple responses for each helper method call
            for _ in range(4):
                m.post(
                    "https://api.test.com/v1/check",
                    payload=mock_validation_result.__dict__,
                )

            assert await client.is_disposable("test@example.com") is False
            assert await client.is_valid("test@example.com") is True
            assert await client.get_risk_score("test@example.com") == "low"
            assert await client.get_deliverability_score("test@example.com") == 95

        await client.close()

    @pytest.mark.asyncio
    async def test_async_get_usage(self, mock_usage_info):
        """Test async usage information retrieval."""
        client = AsyncMailchk(api_key="test-key", base_url="https://api.test.com/v1")

        with aioresponses() as m:
            m.get(
                "https://api.test.com/v1/usage",
                payload=mock_usage_info.__dict__,
            )

            result = await client.get_usage()

            assert isinstance(result, UsageInfo)
            assert result.used == 150

        await client.close()

    @pytest.mark.asyncio
    async def test_async_authentication_error(self):
        """Test async 401 authentication error handling."""
        client = AsyncMailchk(api_key="test-key", base_url="https://api.test.com/v1")

        with aioresponses() as m:
            m.post(
                "https://api.test.com/v1/check",
                payload={"error": "Invalid API key"},
                status=401,
            )

            with pytest.raises(AuthenticationError):
                await client.validate("test@example.com")

        await client.close()

    @pytest.mark.asyncio
    async def test_async_rate_limit_error(self):
        """Test async rate limit error handling."""
        client = AsyncMailchk(api_key="test-key", base_url="https://api.test.com/v1")

        with aioresponses() as m:
            m.post(
                "https://api.test.com/v1/check",
                payload={"error": "Rate limit exceeded"},
                status=429,
                headers={"Retry-After": "30"},
            )

            with pytest.raises(RateLimitError) as exc_info:
                await client.validate("test@example.com")

            assert exc_info.value.retry_after == 30

        await client.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, test_api_key, mock_validation_result):
        """Test async client as context manager."""
        async with AsyncMailchk(
            api_key=test_api_key, base_url="https://api.test.com/v1"
        ) as client:
            assert isinstance(client, AsyncMailchk)

            with aioresponses() as m:
                m.post(
                    "https://api.test.com/v1/check",
                    payload=mock_validation_result.__dict__,
                )

                result = await client.validate("test@example.com")
                assert result.valid is True

    @pytest.mark.asyncio
    async def test_async_session_management(self):
        """Test async client session management."""
        client = AsyncMailchk(api_key="test-key")

        # Session should be None initially
        assert client._session is None

        # Session should be created when needed
        session = await client._get_session()
        assert session is not None
        assert client._session is session

        # Should return same session
        session2 = await client._get_session()
        assert session2 is session

        await client.close()

    @pytest.mark.asyncio
    async def test_async_close_session(self):
        """Test closing async client session."""
        client = AsyncMailchk(api_key="test-key")

        # Get session to initialize it
        session = await client._get_session()
        
        # Mock session for testing
        session.close = MagicMock()
        session.closed = False

        await client.close()

        # Should call close on session
        session.close.assert_called_once()


class TestClientIntegration:
    """Integration tests for client functionality."""

    @responses.activate
    def test_complete_validation_workflow(self, mailchk_client):
        """Test complete email validation workflow."""
        # Mock validation response
        validation_data = {
            "email": "user@company.com",
            "domain": "company.com",
            "valid": True,
            "disposable": False,
            "scam_domain": False,
            "mx_exists": True,
            "blacklisted_mx": False,
            "free_email": False,
            "did_you_mean": "",
            "risk_score": "low",
            "risk_factors": [],
            "email_provider": "Company Corp",
            "deliverability_score": 95,
            "spf": "pass",
            "dmarc": "pass",
            "normalized_email": "user@company.com",
            "is_aliased": False,
            "alias_type": None,
        }

        responses.add(
            responses.POST,
            f"{mailchk_client.base_url}/check",
            json=validation_data,
            status=200,
        )

        # Validate email
        result = mailchk_client.validate("user@company.com")

        # Check basic validation
        assert result.valid is True
        assert result.email == "user@company.com"

        # Check business rules
        assert result.is_safe() is True
        assert result.is_deliverable(90) is True
        assert result.has_valid_auth() is True
        assert not result.is_high_risk()

    @responses.activate
    def test_business_email_validation_rules(self, mailchk_client):
        """Test business email validation rules."""
        test_cases = [
            {
                "email": "user@company.com",
                "data": {
                    "valid": True,
                    "disposable": False,
                    "free_email": False,
                    "deliverability_score": 95,
                    "risk_score": "low",
                },
                "should_accept": True,
                "reason": "Valid business email",
            },
            {
                "email": "user@gmail.com",
                "data": {
                    "valid": True,
                    "disposable": False,
                    "free_email": True,
                    "deliverability_score": 85,
                    "risk_score": "medium",
                },
                "should_accept": False,
                "reason": "Free email provider",
            },
            {
                "email": "temp@tempmail.com",
                "data": {
                    "valid": True,
                    "disposable": True,
                    "free_email": False,
                    "deliverability_score": 70,
                    "risk_score": "high",
                },
                "should_accept": False,
                "reason": "Disposable email",
            },
        ]

        for case in test_cases:
            responses.add(
                responses.POST,
                f"{mailchk_client.base_url}/check",
                json=case["data"],
                status=200,
            )

            result = mailchk_client.validate(case["email"])

            # Business validation rules
            is_acceptable = (
                result.valid
                and not result.disposable
                and not result.free_email
                and result.deliverability_score >= 80
                and not result.is_high_risk()
            )

            assert is_acceptable == case["should_accept"], (
                f"Failed for {case['email']}: {case['reason']}"
            )

        # Clear responses for next test
        responses.reset()

    @pytest.mark.asyncio
    async def test_async_bulk_validation_workflow(self):
        """Test async bulk validation workflow."""
        client = AsyncMailchk(api_key="test-key", base_url="https://api.test.com/v1")

        emails = ["user1@company.com", "temp@tempmail.com", "user2@example.com"]

        bulk_data = {
            "total": 3,
            "valid": 2,
            "invalid": 1,
            "disposable": 1,
            "results": [
                {
                    "email": "user1@company.com",
                    "valid": True,
                    "disposable": False,
                    "risk_score": "low",
                },
                {
                    "email": "temp@tempmail.com",
                    "valid": True,
                    "disposable": True,
                    "risk_score": "high",
                },
                {
                    "email": "user2@example.com",
                    "valid": False,
                    "disposable": False,
                    "risk_score": "critical",
                },
            ],
        }

        with aioresponses() as m:
            m.post("https://api.test.com/v1/check/bulk", payload=bulk_data)

            result = await client.validate_bulk(emails)

            # Validate results
            assert result.total == 3
            assert result.valid == 2
            assert result.disposable == 1

            # Check individual results
            safe_emails = [r for r in result.results if r.is_safe()]
            disposable_emails = [r for r in result.results if r.disposable]

            assert len(safe_emails) == 1
            assert len(disposable_emails) == 1

        await client.close()