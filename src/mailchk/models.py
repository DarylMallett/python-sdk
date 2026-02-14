"""Mailchk SDK data models."""

from dataclasses import dataclass
from typing import Literal


RiskLevel = Literal["low", "medium", "high", "critical"]


@dataclass
class ValidationResult:
    """Result of an email validation check."""

    email: str
    valid: bool
    disposable: bool
    mx_valid: bool
    risk: RiskLevel
    risk_score: int
    domain: str
    reason: str | None = None
    suggestion: str | None = None
    cached: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationResult":
        """Create a ValidationResult from API response dictionary."""
        return cls(
            email=data.get("email", ""),
            valid=data.get("valid", False),
            disposable=data.get("disposable", False),
            mx_valid=data.get("mx_valid", True),
            risk=data.get("risk", "low"),
            risk_score=data.get("risk_score", 0),
            domain=data.get("domain", ""),
            reason=data.get("reason"),
            suggestion=data.get("suggestion"),
            cached=data.get("cached", False),
        )

    def is_safe(self) -> bool:
        """Check if the email is safe to use (valid and low risk)."""
        return self.valid and self.risk in ("low", "medium")

    def is_disposable(self) -> bool:
        """Check if the email is from a disposable provider."""
        return self.disposable

    def is_high_risk(self) -> bool:
        """Check if the email has high or critical risk."""
        return self.risk in ("high", "critical")


@dataclass
class BulkValidationResult:
    """Result of a bulk email validation."""

    total: int
    valid: int
    invalid: int
    disposable: int
    results: list[ValidationResult]

    @classmethod
    def from_dict(cls, data: dict) -> "BulkValidationResult":
        """Create a BulkValidationResult from API response dictionary."""
        results = [
            ValidationResult.from_dict(r) for r in data.get("results", [])
        ]
        return cls(
            total=data.get("total", len(results)),
            valid=data.get("valid", sum(1 for r in results if r.valid)),
            invalid=data.get("invalid", sum(1 for r in results if not r.valid)),
            disposable=data.get(
                "disposable", sum(1 for r in results if r.disposable)
            ),
            results=results,
        )


@dataclass
class UsageInfo:
    """API usage information."""

    used: int
    limit: int
    remaining: int
    reset_date: str

    @classmethod
    def from_dict(cls, data: dict) -> "UsageInfo":
        """Create a UsageInfo from API response dictionary."""
        used = data.get("used", 0)
        limit = data.get("limit", 0)
        return cls(
            used=used,
            limit=limit,
            remaining=data.get("remaining", limit - used),
            reset_date=data.get("reset_date", ""),
        )

    @property
    def percentage_used(self) -> float:
        """Get the percentage of quota used."""
        if self.limit == 0:
            return 0.0
        return (self.used / self.limit) * 100
