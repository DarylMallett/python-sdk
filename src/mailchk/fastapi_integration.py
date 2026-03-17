"""FastAPI and Pydantic integration for Mailchk email validation."""

from typing import Any, Dict, Optional, Callable
import asyncio

try:
    from pydantic import BaseModel, Field, validator
    from pydantic.fields import ModelField
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object
    Field = lambda *args, **kwargs: None
    validator = lambda *args, **kwargs: lambda f: f
    ModelField = object

try:
    from fastapi import HTTPException, Depends
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    HTTPException = Exception
    Depends = lambda f: f

from .client import Mailchk, AsyncMailchk
from .models import ValidationResult, BulkValidationResult, UsageInfo
from .exceptions import MailchkError, AuthenticationError
from .config import from_environment


# Global client instances for FastAPI dependency injection
_async_client: Optional[AsyncMailchk] = None


def get_async_client() -> AsyncMailchk:
    """
    Get the configured async Mailchk client for FastAPI dependency injection.
    
    Example:
        >>> from fastapi import FastAPI, Depends
        >>> from mailchk.fastapi_integration import get_async_client, configure_fastapi
        >>> 
        >>> app = FastAPI()
        >>> configure_fastapi(api_key="your-api-key")
        >>> 
        >>> @app.post("/validate")
        >>> async def validate_email(
        ...     email: str,
        ...     client: AsyncMailchk = Depends(get_async_client)
        ... ):
        ...     return await client.validate(email)
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is not installed. Install with: pip install mailchk[fastapi]")
    
    global _async_client
    if _async_client is None:
        raise HTTPException(
            status_code=500,
            detail="Mailchk not configured. Call configure_fastapi() first."
        )
    return _async_client


def configure_fastapi(
    api_key: Optional[str] = None,
    env_file: Optional[str] = None,
    **kwargs
) -> None:
    """
    Configure Mailchk for FastAPI applications.
    
    Args:
        api_key: API key (if None, will load from environment)
        env_file: Optional path to .env file
        **kwargs: Additional client configuration
        
    Example:
        >>> from fastapi import FastAPI
        >>> from mailchk.fastapi_integration import configure_fastapi
        >>> 
        >>> app = FastAPI()
        >>> configure_fastapi(api_key="your-api-key")
        >>> 
        >>> # Or from environment
        >>> configure_fastapi()
    """
    global _async_client
    
    if api_key:
        config = {"api_key": api_key, **kwargs}
    else:
        config = from_environment(env_file=env_file, **kwargs)
    
    _async_client = AsyncMailchk(**config)


# Pydantic Models for API responses
if PYDANTIC_AVAILABLE:
    class ValidationResponse(BaseModel):
        """Pydantic model for email validation responses."""
        
        email: str = Field(..., description="The validated email address")
        domain: str = Field(..., description="The email domain")
        valid: bool = Field(..., description="Whether the email is valid")
        disposable: bool = Field(..., description="Whether it's a disposable email")
        scam_domain: bool = Field(..., description="Whether the domain is flagged as scam")
        mx_exists: bool = Field(..., description="Whether the domain has MX records")
        blacklisted_mx: bool = Field(..., description="Whether MX host is blacklisted")
        free_email: bool = Field(..., description="Whether it's a free email provider")
        did_you_mean: str = Field(..., description="Suggested correction for typos")
        risk_score: str = Field(..., description="Risk level: low, medium, high, critical")
        risk_factors: list[str] = Field(..., description="List of risk factors")
        email_provider: Optional[str] = Field(..., description="Detected email provider")
        deliverability_score: int = Field(..., description="Deliverability score (0-100)")
        spf: str = Field(..., description="SPF record status")
        dmarc: str = Field(..., description="DMARC record status")
        normalized_email: str = Field(..., description="Normalized form of the email")
        is_aliased: bool = Field(..., description="Whether the email uses aliasing")
        alias_type: Optional[str] = Field(..., description="Type of alias used")
        reason: Optional[str] = Field(None, description="Reason if invalid")
        
        # Helper properties
        is_safe: bool = Field(..., description="Whether email is safe to use")
        is_high_risk: bool = Field(..., description="Whether email has high risk")
        has_valid_auth: bool = Field(..., description="Whether domain has valid SPF/DMARC")
        
        @classmethod
        def from_validation_result(cls, result: ValidationResult) -> "ValidationResponse":
            """Create from ValidationResult."""
            return cls(
                email=result.email,
                domain=result.domain,
                valid=result.valid,
                disposable=result.disposable,
                scam_domain=result.scam_domain,
                mx_exists=result.mx_exists,
                blacklisted_mx=result.blacklisted_mx,
                free_email=result.free_email,
                did_you_mean=result.did_you_mean,
                risk_score=result.risk_score,
                risk_factors=result.risk_factors,
                email_provider=result.email_provider,
                deliverability_score=result.deliverability_score,
                spf=result.spf,
                dmarc=result.dmarc,
                normalized_email=result.normalized_email,
                is_aliased=result.is_aliased,
                alias_type=result.alias_type,
                reason=result.reason,
                is_safe=result.is_safe(),
                is_high_risk=result.is_high_risk(),
                has_valid_auth=result.has_valid_auth(),
            )


    class BulkValidationResponse(BaseModel):
        """Pydantic model for bulk validation responses."""
        
        total: int = Field(..., description="Total number of emails validated")
        valid: int = Field(..., description="Number of valid emails")
        invalid: int = Field(..., description="Number of invalid emails")
        disposable: int = Field(..., description="Number of disposable emails")
        results: list[ValidationResponse] = Field(..., description="Individual validation results")
        
        @classmethod
        def from_bulk_result(cls, result: BulkValidationResult) -> "BulkValidationResponse":
            """Create from BulkValidationResult."""
            return cls(
                total=result.total,
                valid=result.valid,
                invalid=result.invalid,
                disposable=result.disposable,
                results=[
                    ValidationResponse.from_validation_result(r) 
                    for r in result.results
                ]
            )


    class UsageResponse(BaseModel):
        """Pydantic model for usage information responses."""
        
        used: int = Field(..., description="Number of validations used")
        limit: int = Field(..., description="Validation limit for the plan")
        remaining: int = Field(..., description="Remaining validations")
        reset_date: str = Field(..., description="When the quota resets")
        percentage_used: float = Field(..., description="Percentage of quota used")
        
        @classmethod
        def from_usage_info(cls, usage: UsageInfo) -> "UsageResponse":
            """Create from UsageInfo."""
            return cls(
                used=usage.used,
                limit=usage.limit,
                remaining=usage.remaining,
                reset_date=usage.reset_date,
                percentage_used=usage.percentage_used
            )


    # Request models
    class EmailValidationRequest(BaseModel):
        """Request model for email validation."""
        
        email: str = Field(..., description="Email address to validate", example="user@example.com")
        
        @validator('email')
        def validate_email_format(cls, v):
            if not v or '@' not in v:
                raise ValueError('Invalid email format')
            return v.strip().lower()


    class BulkEmailValidationRequest(BaseModel):
        """Request model for bulk email validation."""
        
        emails: list[str] = Field(
            ..., 
            description="List of email addresses to validate",
            min_items=1,
            max_items=100,
            example=["user1@example.com", "user2@gmail.com"]
        )
        
        @validator('emails')
        def validate_emails(cls, v):
            if len(v) > 100:
                raise ValueError('Maximum 100 emails per request')
            
            cleaned = []
            for email in v:
                if not email or '@' not in email:
                    raise ValueError(f'Invalid email format: {email}')
                cleaned.append(email.strip().lower())
            
            return cleaned


    # Custom Pydantic field for email validation
    def EmailValidationField(
        allow_disposable: bool = True,
        allow_free_email: bool = True,
        min_deliverability: int = 50,
        max_risk_level: str = "critical"
    ):
        """
        Create a Pydantic field that validates emails using Mailchk.
        
        Args:
            allow_disposable: Allow disposable/temporary emails
            allow_free_email: Allow free email providers
            min_deliverability: Minimum deliverability score (0-100)
            max_risk_level: Maximum allowed risk level
            
        Example:
            >>> class UserSignup(BaseModel):
            ...     email: str = EmailValidationField(
            ...         allow_disposable=False,
            ...         min_deliverability=70
            ...     )
        """
        def validate_email(cls, v: str, field: ModelField) -> str:
            # Get client - this would need to be configured
            try:
                client = get_async_client()
                # Note: This is a sync validator, so we can't use async client directly
                # In practice, you'd want to use the sync client or handle this differently
                sync_client = Mailchk(api_key=client.api_key, base_url=client.base_url, timeout=client.timeout)
                result = sync_client.validate(v)
                
                if not result.valid:
                    raise ValueError(result.reason or "Email address is not valid")
                
                if not allow_disposable and result.disposable:
                    raise ValueError("Disposable email addresses are not allowed")
                
                if not allow_free_email and result.free_email:
                    raise ValueError("Please use your work email address")
                
                if result.deliverability_score < min_deliverability:
                    raise ValueError(f"Email deliverability score too low: {result.deliverability_score}")
                
                risk_levels = ["low", "medium", "high", "critical"]
                max_risk_index = risk_levels.index(max_risk_level)
                current_risk_index = risk_levels.index(result.risk_score)
                
                if current_risk_index > max_risk_index:
                    raise ValueError(f"Email has high risk factors: {', '.join(result.risk_factors)}")
                
                return result.normalized_email
                
            except MailchkError as e:
                raise ValueError(f"Email validation failed: {e.message}")
        
        return Field(
            ...,
            description="Email address (validated with Mailchk)",
            validators=[validate_email]
        )


# FastAPI middleware for request logging
if FASTAPI_AVAILABLE:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    import time
    
    class MailchkLoggingMiddleware(BaseHTTPMiddleware):
        """
        FastAPI middleware to log email validation requests.
        
        Example:
            >>> from fastapi import FastAPI
            >>> from mailchk.fastapi_integration import MailchkLoggingMiddleware
            >>> 
            >>> app = FastAPI()
            >>> app.add_middleware(MailchkLoggingMiddleware)
        """
        
        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            start_time = time.time()
            
            response = await call_next(request)
            
            process_time = time.time() - start_time
            
            # Log email validation requests
            if "/validate" in str(request.url):
                print(f"Mailchk validation request: {request.method} {request.url} - "
                      f"Status: {response.status_code} - Time: {process_time:.3f}s")
            
            return response


# Example FastAPI router
def create_validation_router():
    """
    Create a FastAPI router with email validation endpoints.
    
    Example:
        >>> from fastapi import FastAPI
        >>> from mailchk.fastapi_integration import create_validation_router, configure_fastapi
        >>> 
        >>> app = FastAPI()
        >>> configure_fastapi(api_key="your-api-key")
        >>> 
        >>> validation_router = create_validation_router()
        >>> app.include_router(validation_router, prefix="/api/email", tags=["Email Validation"])
    """
    if not FASTAPI_AVAILABLE or not PYDANTIC_AVAILABLE:
        raise ImportError("FastAPI and Pydantic are required. Install with: pip install mailchk[fastapi]")
    
    from fastapi import APIRouter, HTTPException
    
    router = APIRouter()
    
    @router.post("/validate", response_model=ValidationResponse)
    async def validate_email(
        request: EmailValidationRequest,
        client: AsyncMailchk = Depends(get_async_client)
    ):
        """Validate a single email address."""
        try:
            result = await client.validate(request.email)
            return ValidationResponse.from_validation_result(result)
        except MailchkError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/validate/bulk", response_model=BulkValidationResponse)
    async def validate_emails_bulk(
        request: BulkEmailValidationRequest,
        client: AsyncMailchk = Depends(get_async_client)
    ):
        """Validate multiple email addresses."""
        try:
            result = await client.validate_bulk(request.emails)
            return BulkValidationResponse.from_bulk_result(result)
        except MailchkError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.get("/usage", response_model=UsageResponse)
    async def get_usage(
        client: AsyncMailchk = Depends(get_async_client)
    ):
        """Get API usage information."""
        try:
            usage = await client.get_usage()
            return UsageResponse.from_usage_info(usage)
        except MailchkError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    return router