"""Mailchk SDK data models."""

from dataclasses import dataclass, field
from typing import Literal


RiskLevel = Literal["low", "medium", "high", "critical"]
SpfResult = Literal["pass", "fail", "none"]
DmarcResult = Literal["pass", "fail", "none"]
AliasType = Literal[
    "plus_addressing", "dot_variation", "subdomain_addressing", "provider_alias"
]


@dataclass
class MxRecord:
    """A single MX record for a domain."""

    exchange: str
    priority: int

    @classmethod
    def from_dict(cls, data: dict) -> "MxRecord":
        """Create an MxRecord from a dictionary."""
        return cls(
            exchange=data.get("exchange", ""),
            priority=data.get("priority", 0),
        )


@dataclass
class ValidationResult:
    """Result of an email validation check."""

    email: str
    domain: str
    valid: bool
    disposable: bool
    scam_domain: bool
    mx_exists: bool
    blacklisted_mx: bool
    free_email: bool
    did_you_mean: str
    risk_score: RiskLevel
    risk_factors: list[str]
    email_provider: str | None
    deliverability_score: int
    spf: SpfResult
    dmarc: DmarcResult
    normalized_email: str
    is_aliased: bool
    alias_type: AliasType | None = None
    mx_records: list[MxRecord] = field(default_factory=list)
    reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationResult":
        """Create a ValidationResult from API response dictionary."""
        mx_records_raw = data.get("mx_records") or []
        mx_records = [MxRecord.from_dict(r) for r in mx_records_raw]

        return cls(
            email=data.get("email", ""),
            domain=data.get("domain", ""),
            valid=data.get("valid", False),
            disposable=data.get("disposable", False),
            scam_domain=data.get("scam_domain", False),
            mx_exists=data.get("mx_exists", False),
            mx_records=mx_records,
            blacklisted_mx=data.get("blacklisted_mx", False),
            free_email=data.get("free_email", False),
            did_you_mean=data.get("did_you_mean", ""),
            risk_score=data.get("risk_score", "low"),
            risk_factors=data.get("risk_factors", []),
            reason=data.get("reason"),
            email_provider=data.get("email_provider"),
            deliverability_score=data.get("deliverability_score", 0),
            spf=data.get("spf", "none"),
            dmarc=data.get("dmarc", "none"),
            normalized_email=data.get("normalized_email", ""),
            is_aliased=data.get("is_aliased", False),
            alias_type=data.get("alias_type"),
        )

    def is_safe(self) -> bool:
        """Check if the email is safe to use (valid and low risk)."""
        return self.valid and self.risk_score in ("low", "medium")

    def is_disposable(self) -> bool:
        """Check if the email is from a disposable provider."""
        return self.disposable

    def is_high_risk(self) -> bool:
        """Check if the email has high or critical risk."""
        return self.risk_score in ("high", "critical")

    def is_scam(self) -> bool:
        """Check if the email domain is a known scam domain."""
        return self.scam_domain

    def is_deliverable(self, threshold: int = 50) -> bool:
        """Check if the email meets the deliverability threshold (0-100)."""
        return self.deliverability_score >= threshold

    def has_valid_auth(self) -> bool:
        """Check if the domain has passing SPF and DMARC records."""
        return self.spf == "pass" and self.dmarc == "pass"


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
