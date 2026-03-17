"""Tests for Mailchk exceptions."""

import pytest
from mailchk.exceptions import (
    MailchkError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    APIError,
)


class TestMailchkError:
    """Tests for base MailchkError class."""

    def test_create_mailchk_error(self):
        """Test creating base MailchkError."""
        error = MailchkError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.status_code is None

    def test_create_mailchk_error_with_status_code(self):
        """Test creating MailchkError with status code."""
        error = MailchkError("Test error", status_code=400)

        assert error.message == "Test error"
        assert error.status_code == 400

    def test_mailchk_error_inheritance(self):
        """Test that MailchkError inherits from Exception."""
        error = MailchkError("Test error")

        assert isinstance(error, Exception)
        assert isinstance(error, MailchkError)


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_create_authentication_error_default(self):
        """Test creating AuthenticationError with default message."""
        error = AuthenticationError()

        assert str(error) == "Invalid or missing API key"
        assert error.message == "Invalid or missing API key"
        assert error.status_code == 401

    def test_create_authentication_error_custom(self):
        """Test creating AuthenticationError with custom message."""
        error = AuthenticationError("Custom auth error")

        assert str(error) == "Custom auth error"
        assert error.message == "Custom auth error"
        assert error.status_code == 401

    def test_authentication_error_inheritance(self):
        """Test AuthenticationError inheritance."""
        error = AuthenticationError()

        assert isinstance(error, MailchkError)
        assert isinstance(error, Exception)


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_create_rate_limit_error_default(self):
        """Test creating RateLimitError with default values."""
        error = RateLimitError()

        assert str(error) == "Rate limit exceeded"
        assert error.message == "Rate limit exceeded"
        assert error.status_code == 429
        assert error.retry_after is None

    def test_create_rate_limit_error_with_retry_after(self):
        """Test creating RateLimitError with retry_after value."""
        error = RateLimitError("Custom rate limit message", retry_after=60)

        assert str(error) == "Custom rate limit message"
        assert error.message == "Custom rate limit message"
        assert error.status_code == 429
        assert error.retry_after == 60

    def test_rate_limit_error_inheritance(self):
        """Test RateLimitError inheritance."""
        error = RateLimitError()

        assert isinstance(error, MailchkError)
        assert isinstance(error, Exception)

    def test_rate_limit_error_retry_after_property(self):
        """Test retry_after property behavior."""
        # Without retry_after
        error1 = RateLimitError()
        assert error1.retry_after is None

        # With retry_after
        error2 = RateLimitError(retry_after=30)
        assert error2.retry_after == 30

        # With zero retry_after
        error3 = RateLimitError(retry_after=0)
        assert error3.retry_after == 0


class TestValidationError:
    """Tests for ValidationError."""

    def test_create_validation_error(self):
        """Test creating ValidationError."""
        error = ValidationError("Invalid email format")

        assert str(error) == "Invalid email format"
        assert error.message == "Invalid email format"
        assert error.status_code == 400

    def test_validation_error_inheritance(self):
        """Test ValidationError inheritance."""
        error = ValidationError("Test validation error")

        assert isinstance(error, MailchkError)
        assert isinstance(error, Exception)

    def test_validation_error_requires_message(self):
        """Test that ValidationError requires a message."""
        # This should work
        error = ValidationError("Required message")
        assert error.message == "Required message"

        # Empty string should still work
        error_empty = ValidationError("")
        assert error_empty.message == ""


class TestAPIError:
    """Tests for APIError."""

    def test_create_api_error_default(self):
        """Test creating APIError with default values."""
        error = APIError("Server error occurred")

        assert str(error) == "Server error occurred"
        assert error.message == "Server error occurred"
        assert error.status_code is None

    def test_create_api_error_with_status_code(self):
        """Test creating APIError with status code."""
        error = APIError("Internal server error", status_code=500)

        assert str(error) == "Internal server error"
        assert error.message == "Internal server error"
        assert error.status_code == 500

    def test_api_error_inheritance(self):
        """Test APIError inheritance."""
        error = APIError("Test API error")

        assert isinstance(error, MailchkError)
        assert isinstance(error, Exception)

    def test_api_error_with_various_status_codes(self):
        """Test APIError with different status codes."""
        # Server errors
        error_500 = APIError("Server error", status_code=500)
        assert error_500.status_code == 500

        error_502 = APIError("Bad gateway", status_code=502)
        assert error_502.status_code == 502

        # Client errors
        error_404 = APIError("Not found", status_code=404)
        assert error_404.status_code == 404

        error_422 = APIError("Unprocessable entity", status_code=422)
        assert error_422.status_code == 422


class TestExceptionHierarchy:
    """Tests for exception hierarchy and relationships."""

    def test_all_exceptions_inherit_from_mailchk_error(self):
        """Test that all custom exceptions inherit from MailchkError."""
        exceptions = [
            AuthenticationError("test"),
            RateLimitError("test"),
            ValidationError("test"),
            APIError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, MailchkError)
            assert isinstance(exc, Exception)

    def test_exception_catching(self):
        """Test that exceptions can be caught by their base class."""
        # Test catching specific exceptions
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Auth error")

        with pytest.raises(RateLimitError):
            raise RateLimitError("Rate limit error")

        # Test catching by base class
        with pytest.raises(MailchkError):
            raise AuthenticationError("Auth error caught as MailchkError")

        with pytest.raises(MailchkError):
            raise ValidationError("Validation error caught as MailchkError")

        # Test catching by Exception base class
        with pytest.raises(Exception):
            raise APIError("API error caught as Exception")

    def test_exception_properties_preserved(self):
        """Test that exception properties are preserved in inheritance."""
        # Create each exception type
        auth_error = AuthenticationError("Auth message")
        rate_error = RateLimitError("Rate message", retry_after=30)
        validation_error = ValidationError("Validation message")
        api_error = APIError("API message", status_code=500)

        # Test that they all have the base MailchkError properties
        for error in [auth_error, rate_error, validation_error, api_error]:
            assert hasattr(error, 'message')
            assert hasattr(error, 'status_code')
            assert error.message is not None
            assert isinstance(error.message, str)

        # Test specific properties
        assert auth_error.status_code == 401
        assert rate_error.status_code == 429
        assert rate_error.retry_after == 30
        assert validation_error.status_code == 400
        assert api_error.status_code == 500

    def test_exception_string_representation(self):
        """Test string representation of exceptions."""
        auth_error = AuthenticationError("Invalid API key")
        assert str(auth_error) == "Invalid API key"

        rate_error = RateLimitError("Too many requests", retry_after=60)
        assert str(rate_error) == "Too many requests"

        validation_error = ValidationError("Bad email format")
        assert str(validation_error) == "Bad email format"

        api_error = APIError("Server is down")
        assert str(api_error) == "Server is down"