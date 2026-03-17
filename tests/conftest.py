"""Test configuration and fixtures for Mailchk SDK tests."""

import os
import pytest
import responses
from unittest.mock import patch

from mailchk import Mailchk, AsyncMailchk
from mailchk.models import ValidationResult, BulkValidationResult, UsageInfo, MxRecord


@pytest.fixture(autouse=True)
def clear_env_vars():
    """Clear environment variables before each test."""
    env_vars = [
        "MAILCHK_API_KEY",
        "MAILCHK_BASE_URL", 
        "MAILCHK_TIMEOUT",
        "MAILCHK_RETRY_ATTEMPTS",
        "MAILCHK_RETRY_DELAY",
    ]
    
    original_values = {}
    for var in env_vars:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value


@pytest.fixture
def test_api_key():
    """Test API key fixture."""
    return "test-api-key-12345"


@pytest.fixture
def test_base_url():
    """Test base URL fixture."""
    return "https://api.test.com/v1"


@pytest.fixture
def mailchk_client(test_api_key, test_base_url):
    """Create a test Mailchk client."""
    return Mailchk(
        api_key=test_api_key,
        base_url=test_base_url,
        timeout=30,
        retry_attempts=2,
        retry_delay=0.1,
    )


@pytest.fixture
async def async_mailchk_client(test_api_key, test_base_url):
    """Create a test AsyncMailchk client."""
    client = AsyncMailchk(
        api_key=test_api_key,
        base_url=test_base_url,
        timeout=30,
        retry_attempts=2,
        retry_delay=0.1,
    )
    yield client
    await client.close()


@pytest.fixture
def mock_validation_result():
    """Mock ValidationResult for testing."""
    return ValidationResult(
        email="test@example.com",
        domain="example.com",
        valid=True,
        disposable=False,
        scam_domain=False,
        mx_exists=True,
        blacklisted_mx=False,
        free_email=False,
        did_you_mean="",
        risk_score="low",
        risk_factors=[],
        email_provider="Example Corp",
        deliverability_score=95,
        spf="pass",
        dmarc="pass",
        normalized_email="test@example.com",
        is_aliased=False,
        alias_type=None,
        mx_records=[MxRecord(exchange="mail.example.com", priority=10)],
        reason=None,
    )


@pytest.fixture
def mock_disposable_result():
    """Mock ValidationResult for disposable email."""
    return ValidationResult(
        email="temp@tempmail.com",
        domain="tempmail.com",
        valid=True,
        disposable=True,
        scam_domain=False,
        mx_exists=True,
        blacklisted_mx=False,
        free_email=False,
        did_you_mean="",
        risk_score="high",
        risk_factors=["disposable_provider"],
        email_provider="TempMail",
        deliverability_score=60,
        spf="none",
        dmarc="none",
        normalized_email="temp@tempmail.com",
        is_aliased=False,
        alias_type=None,
        mx_records=[],
        reason=None,
    )


@pytest.fixture
def mock_invalid_result():
    """Mock ValidationResult for invalid email."""
    return ValidationResult(
        email="invalid@nonexistent.com",
        domain="nonexistent.com",
        valid=False,
        disposable=False,
        scam_domain=False,
        mx_exists=False,
        blacklisted_mx=False,
        free_email=False,
        did_you_mean="invalid@nonexistent.org",
        risk_score="critical",
        risk_factors=["no_mx_record"],
        email_provider=None,
        deliverability_score=0,
        spf="none",
        dmarc="none",
        normalized_email="invalid@nonexistent.com",
        is_aliased=False,
        alias_type=None,
        mx_records=[],
        reason="Domain does not exist",
    )


@pytest.fixture
def mock_bulk_result(mock_validation_result, mock_disposable_result, mock_invalid_result):
    """Mock BulkValidationResult for testing."""
    return BulkValidationResult(
        total=3,
        valid=2,
        invalid=1,
        disposable=1,
        results=[mock_validation_result, mock_disposable_result, mock_invalid_result],
    )


@pytest.fixture
def mock_usage_info():
    """Mock UsageInfo for testing."""
    return UsageInfo(
        used=150,
        limit=1000,
        remaining=850,
        reset_date="2024-01-31T00:00:00Z",
    )


@pytest.fixture
def responses_mock():
    """Responses mock fixture for HTTP mocking."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def set_env_vars():
    """Fixture to set environment variables for testing."""
    def _set_env_vars(**kwargs):
        for key, value in kwargs.items():
            os.environ[key] = str(value)
    return _set_env_vars