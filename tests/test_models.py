"""Tests for Mailchk data models."""

import pytest
from mailchk.models import (
    ValidationResult,
    BulkValidationResult,
    UsageInfo,
    MxRecord,
)


class TestMxRecord:
    """Tests for MxRecord model."""

    def test_create_mx_record(self):
        """Test creating MxRecord from data."""
        data = {"exchange": "mail.example.com", "priority": 10}
        mx_record = MxRecord.from_dict(data)

        assert mx_record.exchange == "mail.example.com"
        assert mx_record.priority == 10

    def test_create_mx_record_missing_data(self):
        """Test creating MxRecord with missing data uses defaults."""
        data = {}
        mx_record = MxRecord.from_dict(data)

        assert mx_record.exchange == ""
        assert mx_record.priority == 0

    def test_mx_record_dataclass_behavior(self):
        """Test MxRecord dataclass behavior."""
        record1 = MxRecord("mail.example.com", 10)
        record2 = MxRecord("mail.example.com", 10)
        record3 = MxRecord("mail2.example.com", 20)

        assert record1 == record2
        assert record1 != record3
        assert str(record1) == "MxRecord(exchange='mail.example.com', priority=10)"


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_create_validation_result(self):
        """Test creating ValidationResult from API data."""
        data = {
            "email": "test@example.com",
            "domain": "example.com",
            "valid": True,
            "disposable": False,
            "scam_domain": False,
            "mx_exists": True,
            "mx_records": [{"exchange": "mail.example.com", "priority": 10}],
            "blacklisted_mx": False,
            "free_email": False,
            "did_you_mean": "",
            "risk_score": "low",
            "risk_factors": [],
            "email_provider": "Example Corp",
            "deliverability_score": 95,
            "spf": "pass",
            "dmarc": "pass",
            "normalized_email": "test@example.com",
            "is_aliased": False,
            "alias_type": None,
            "reason": None,
        }

        result = ValidationResult.from_dict(data)

        assert result.email == "test@example.com"
        assert result.domain == "example.com"
        assert result.valid is True
        assert result.disposable is False
        assert result.risk_score == "low"
        assert result.deliverability_score == 95
        assert len(result.mx_records) == 1
        assert result.mx_records[0].exchange == "mail.example.com"

    def test_create_validation_result_minimal_data(self):
        """Test creating ValidationResult with minimal data."""
        data = {}
        result = ValidationResult.from_dict(data)

        assert result.email == ""
        assert result.domain == ""
        assert result.valid is False
        assert result.disposable is False
        assert result.deliverability_score == 0
        assert result.mx_records == []
        assert result.risk_score == "low"

    def test_is_safe_method(self):
        """Test is_safe helper method."""
        # Safe email (valid and low risk)
        safe_result = ValidationResult(
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
            email_provider="Example",
            deliverability_score=95,
            spf="pass",
            dmarc="pass",
            normalized_email="test@example.com",
            is_aliased=False,
        )

        assert safe_result.is_safe() is True

        # Medium risk is still considered safe
        medium_result = safe_result.__class__(
            **{**safe_result.__dict__, "risk_score": "medium"}
        )
        assert medium_result.is_safe() is True

        # High risk is not safe
        high_risk_result = safe_result.__class__(
            **{**safe_result.__dict__, "risk_score": "high"}
        )
        assert high_risk_result.is_safe() is False

        # Invalid email is not safe
        invalid_result = safe_result.__class__(
            **{**safe_result.__dict__, "valid": False}
        )
        assert invalid_result.is_safe() is False

    def test_is_high_risk_method(self):
        """Test is_high_risk helper method."""
        result = ValidationResult(
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
            email_provider="Example",
            deliverability_score=95,
            spf="pass",
            dmarc="pass",
            normalized_email="test@example.com",
            is_aliased=False,
        )

        # Low risk
        assert result.is_high_risk() is False

        # Medium risk
        result.risk_score = "medium"
        assert result.is_high_risk() is False

        # High risk
        result.risk_score = "high"
        assert result.is_high_risk() is True

        # Critical risk
        result.risk_score = "critical"
        assert result.is_high_risk() is True

    def test_is_deliverable_method(self):
        """Test is_deliverable helper method."""
        result = ValidationResult(
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
            email_provider="Example",
            deliverability_score=75,
            spf="pass",
            dmarc="pass",
            normalized_email="test@example.com",
            is_aliased=False,
        )

        # Default threshold (50)
        assert result.is_deliverable() is True
        assert result.is_deliverable(50) is True

        # Custom threshold
        assert result.is_deliverable(80) is False
        assert result.is_deliverable(70) is True

        # Zero score
        result.deliverability_score = 0
        assert result.is_deliverable() is False
        assert result.is_deliverable(0) is True

    def test_has_valid_auth_method(self):
        """Test has_valid_auth helper method."""
        result = ValidationResult(
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
            email_provider="Example",
            deliverability_score=95,
            spf="pass",
            dmarc="pass",
            normalized_email="test@example.com",
            is_aliased=False,
        )

        # Both pass
        assert result.has_valid_auth() is True

        # SPF fail
        result.spf = "fail"
        assert result.has_valid_auth() is False

        # DMARC fail
        result.spf = "pass"
        result.dmarc = "fail"
        assert result.has_valid_auth() is False

        # Both fail
        result.spf = "fail"
        result.dmarc = "fail"
        assert result.has_valid_auth() is False

        # None values
        result.spf = "none"
        result.dmarc = "none"
        assert result.has_valid_auth() is False


class TestBulkValidationResult:
    """Tests for BulkValidationResult model."""

    def test_create_bulk_validation_result(self):
        """Test creating BulkValidationResult from API data."""
        data = {
            "total": 3,
            "valid": 2,
            "invalid": 1,
            "disposable": 1,
            "results": [
                {
                    "email": "valid@example.com",
                    "valid": True,
                    "disposable": False,
                    "deliverability_score": 95,
                },
                {
                    "email": "temp@tempmail.com",
                    "valid": True,
                    "disposable": True,
                    "deliverability_score": 60,
                },
                {
                    "email": "invalid@fake.com",
                    "valid": False,
                    "disposable": False,
                    "deliverability_score": 0,
                },
            ],
        }

        result = BulkValidationResult.from_dict(data)

        assert result.total == 3
        assert result.valid == 2
        assert result.invalid == 1
        assert result.disposable == 1
        assert len(result.results) == 3
        assert result.results[0].email == "valid@example.com"
        assert result.results[1].disposable is True
        assert result.results[2].valid is False

    def test_bulk_result_calculates_stats(self):
        """Test that BulkValidationResult calculates stats from results when missing."""
        data = {
            "results": [
                {"email": "valid1@example.com", "valid": True, "disposable": False},
                {"email": "valid2@example.com", "valid": True, "disposable": False},
                {"email": "temp@tempmail.com", "valid": True, "disposable": True},
                {"email": "invalid@fake.com", "valid": False, "disposable": False},
            ]
        }

        result = BulkValidationResult.from_dict(data)

        assert result.total == 4  # Calculated from length
        assert result.valid == 3  # Calculated from results
        assert result.invalid == 1  # Calculated from results
        assert result.disposable == 1  # Calculated from results


class TestUsageInfo:
    """Tests for UsageInfo model."""

    def test_create_usage_info(self):
        """Test creating UsageInfo from API data."""
        data = {
            "used": 150,
            "limit": 1000,
            "remaining": 850,
            "reset_date": "2024-01-31T00:00:00Z",
        }

        usage = UsageInfo.from_dict(data)

        assert usage.used == 150
        assert usage.limit == 1000
        assert usage.remaining == 850
        assert usage.reset_date == "2024-01-31T00:00:00Z"

    def test_usage_info_calculates_remaining(self):
        """Test that UsageInfo calculates remaining when missing."""
        data = {"used": 150, "limit": 1000}

        usage = UsageInfo.from_dict(data)

        assert usage.remaining == 850  # Calculated: limit - used

    def test_percentage_used_property(self):
        """Test percentage_used property calculation."""
        usage = UsageInfo(used=250, limit=1000, remaining=750, reset_date="2024-01-31")

        assert usage.percentage_used == 25.0

        # Test with zero limit
        usage_zero = UsageInfo(used=0, limit=0, remaining=0, reset_date="2024-01-31")
        assert usage_zero.percentage_used == 0.0

        # Test with full usage
        usage_full = UsageInfo(used=1000, limit=1000, remaining=0, reset_date="2024-01-31")
        assert usage_full.percentage_used == 100.0

    def test_usage_info_defaults(self):
        """Test UsageInfo with minimal data uses defaults."""
        data = {}
        usage = UsageInfo.from_dict(data)

        assert usage.used == 0
        assert usage.limit == 0
        assert usage.remaining == 0
        assert usage.reset_date == ""