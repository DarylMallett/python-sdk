# Mailchk Python SDK

Official Python SDK for the [Mailchk](https://mailchk.io) email validation API.

## Installation

```bash
pip install mailchk
```

For async support:

```bash
pip install mailchk[async]
```

## Quick Start

```python
from mailchk import Mailchk

# Initialize the client
client = Mailchk("your-api-key")

# Validate an email
result = client.validate("user@example.com")

if result.valid and not result.disposable:
    print("Email is valid!")
else:
    print(f"Email rejected: {result.reason}")
```

## Features

- **Email Validation** - Check if emails are valid and deliverable
- **Disposable Detection** - Detect temporary/disposable email providers
- **Scam Domain Detection** - Identify known scam and fraud domains
- **Risk Scoring** - Get risk assessment (low, medium, high, critical) with detailed risk factors
- **Deliverability Scoring** - Get a 0-100 deliverability score for each email
- **MX Validation** - Verify domain mail server records and detect blacklisted MX hosts
- **SPF & DMARC Checks** - Verify domain email authentication records
- **Email Normalization** - Get the canonical form of an email address
- **Alias Detection** - Detect plus addressing, dot variations, subdomain addressing, and provider aliases
- **Typo Suggestions** - Get "did you mean" suggestions for misspelled domains
- **Bulk Validation** - Validate up to 100 emails per request
- **Async Support** - Full async/await support with aiohttp

## Usage

### Basic Validation

```python
from mailchk import Mailchk

client = Mailchk("your-api-key")
result = client.validate("test@gmail.com")

print(f"Valid: {result.valid}")
print(f"Disposable: {result.disposable}")
print(f"Risk Score: {result.risk_score}")
print(f"Risk Factors: {result.risk_factors}")
print(f"Deliverability: {result.deliverability_score}/100")
print(f"SPF: {result.spf}")
print(f"DMARC: {result.dmarc}")
print(f"Provider: {result.email_provider}")
print(f"Normalized: {result.normalized_email}")
```

### Quick Checks

```python
# Check if email is disposable
if client.is_disposable("user@tempmail.com"):
    print("Disposable email detected!")

# Check if email is valid
if client.is_valid("user@gmail.com"):
    print("Email is valid!")

# Get risk level (low, medium, high, critical)
risk = client.get_risk_score("user@example.com")
print(f"Risk level: {risk}")

# Get deliverability score (0-100)
score = client.get_deliverability_score("user@example.com")
print(f"Deliverability score: {score}")
```

### Bulk Validation

```python
emails = [
    "user1@gmail.com",
    "user2@tempmail.com",
    "invalid-email",
    "user3@company.com"
]

result = client.validate_bulk(emails)

print(f"Total: {result.total}")
print(f"Valid: {result.valid}")
print(f"Invalid: {result.invalid}")
print(f"Disposable: {result.disposable}")

for r in result.results:
    status = "PASS" if r.valid else "FAIL"
    print(f"{r.email}: {status} (risk: {r.risk_score}, deliverability: {r.deliverability_score})")
```

### Check Usage

```python
usage = client.get_usage()

print(f"Used: {usage.used}/{usage.limit}")
print(f"Remaining: {usage.remaining}")
print(f"Resets: {usage.reset_date}")
print(f"Usage: {usage.percentage_used:.1f}%")
```

### Async Usage

```python
import asyncio
from mailchk import AsyncMailchk

async def main():
    async with AsyncMailchk("your-api-key") as client:
        # Single validation
        result = await client.validate("user@example.com")
        print(f"Valid: {result.valid}")
        print(f"Deliverability: {result.deliverability_score}")

        # Bulk validation
        emails = ["user1@gmail.com", "user2@yahoo.com"]
        bulk = await client.validate_bulk(emails)
        print(f"Valid: {bulk.valid}/{bulk.total}")

asyncio.run(main())
```

### Context Manager

```python
with Mailchk("your-api-key") as client:
    result = client.validate("user@example.com")
    print(result.valid)
# Connection automatically closed
```

## Error Handling

```python
from mailchk import (
    Mailchk,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    APIError,
)

client = Mailchk("your-api-key")

try:
    result = client.validate("user@example.com")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ValidationError as e:
    print(f"Invalid request: {e.message}")
except APIError as e:
    print(f"API error: {e.message}")
```

## ValidationResult Fields

| Field | Type | Description |
|-------|------|-------------|
| `email` | str | The validated email address |
| `domain` | str | The email domain |
| `valid` | bool | Whether the email is valid |
| `disposable` | bool | Whether it's a disposable/temporary email |
| `scam_domain` | bool | Whether the domain is a known scam domain |
| `mx_exists` | bool | Whether the domain has MX records |
| `mx_records` | list[MxRecord] | MX records with exchange and priority |
| `blacklisted_mx` | bool | Whether MX host is on a blacklist |
| `free_email` | bool | Whether it's a free email provider (Gmail, Yahoo, etc.) |
| `did_you_mean` | str | Suggested correction for misspelled domains |
| `risk_score` | str | Risk level: `low`, `medium`, `high`, or `critical` |
| `risk_factors` | list[str] | Specific reasons contributing to the risk score |
| `reason` | str \| None | Reason if the email is invalid |
| `email_provider` | str \| None | Identified email provider name |
| `deliverability_score` | int | Deliverability score from 0-100 |
| `spf` | str | SPF record status: `pass`, `fail`, or `none` |
| `dmarc` | str | DMARC record status: `pass`, `fail`, or `none` |
| `normalized_email` | str | Canonical/normalized form of the email |
| `is_aliased` | bool | Whether the email uses an alias |
| `alias_type` | str \| None | Alias type: `plus_addressing`, `dot_variation`, `subdomain_addressing`, or `provider_alias` |

### Helper Methods

```python
result = client.validate("user@example.com")

# Check if safe to use (valid and low/medium risk)
if result.is_safe():
    print("Email is safe to use")

# Check if high risk
if result.is_high_risk():
    print("High risk email detected")

# Check if scam domain
if result.is_scam():
    print("Scam domain detected!")

# Check deliverability (default threshold: 50)
if result.is_deliverable():
    print("Email is likely deliverable")

# Check with custom threshold
if result.is_deliverable(threshold=80):
    print("Email has high deliverability")

# Check SPF and DMARC authentication
if result.has_valid_auth():
    print("Domain has valid SPF and DMARC")
```

## Configuration

```python
client = Mailchk(
    api_key="your-api-key",
    base_url="https://api.mailchk.io/v1",  # Custom API URL
    timeout=30,  # Request timeout in seconds
)
```

## Requirements

- Python 3.10+
- requests >= 2.25.0
- aiohttp >= 3.8.0 (for async support)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- Documentation: https://mailchk.io/docs
- Email: support@mailchk.io
- Issues: https://github.com/mailchk/mailchk-python/issues
