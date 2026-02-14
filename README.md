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
- **Risk Scoring** - Get risk assessment (low, medium, high, critical)
- **MX Validation** - Verify domain mail server records
- **Bulk Validation** - Validate up to 200 emails per request
- **Async Support** - Full async/await support with aiohttp

## Usage

### Basic Validation

```python
from mailchk import Mailchk

client = Mailchk("your-api-key")
result = client.validate("test@gmail.com")

print(f"Valid: {result.valid}")
print(f"Disposable: {result.disposable}")
print(f"Risk: {result.risk}")
print(f"Risk Score: {result.risk_score}")
```

### Quick Checks

```python
# Check if email is disposable
if client.is_disposable("user@tempmail.com"):
    print("Disposable email detected!")

# Check if email is valid
if client.is_valid("user@gmail.com"):
    print("Email is valid!")

# Get risk score (0-100)
score = client.get_risk_score("user@example.com")
print(f"Risk score: {score}")
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
    print(f"{r.email}: {'✓' if r.valid else '✗'}")
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

## ValidationResult Properties

| Property | Type | Description |
|----------|------|-------------|
| `email` | str | The validated email address |
| `valid` | bool | Whether the email is valid |
| `disposable` | bool | Whether it's a disposable email |
| `mx_valid` | bool | Whether domain has valid MX records |
| `risk` | str | Risk level: low, medium, high, critical |
| `risk_score` | int | Risk score from 0-100 |
| `domain` | str | The email domain |
| `reason` | str | Reason if invalid |
| `suggestion` | str | Suggested correction if typo detected |
| `cached` | bool | Whether result was from cache |

### Helper Methods

```python
result = client.validate("user@example.com")

# Check if safe to use (valid and low/medium risk)
if result.is_safe():
    print("Email is safe to use")

# Check if high risk
if result.is_high_risk():
    print("High risk email detected")
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

- Python 3.8+
- requests >= 2.25.0
- aiohttp >= 3.8.0 (for async support)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- Documentation: https://mailchk.io/docs
- Email: support@mailchk.io
- Issues: https://github.com/mailchk/mailchk-python/issues
