"""Django integration for Mailchk email validation."""

from typing import Any, Dict, Optional

try:
    from django.core.exceptions import ValidationError as DjangoValidationError
    from django.forms import Field, CharField, EmailField
    from django.contrib import admin
    from django.conf import settings
    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False
    DjangoValidationError = Exception
    Field = object
    CharField = object
    EmailField = object
    admin = None
    settings = None

from .client import Mailchk
from .exceptions import MailchkError, AuthenticationError
from .config import from_environment


def get_django_client() -> Mailchk:
    """
    Get a Mailchk client configured from Django settings.
    
    Settings:
        MAILCHK_API_KEY: Required API key
        MAILCHK_BASE_URL: Optional base URL
        MAILCHK_TIMEOUT: Optional timeout in seconds
        MAILCHK_AUTO_CONFIGURE: If True, auto-configure from environment
        
    Example:
        # In settings.py
        MAILCHK_API_KEY = "your-api-key"
        MAILCHK_TIMEOUT = 30
        
        # In your code
        client = get_django_client()
    """
    if not DJANGO_AVAILABLE:
        raise ImportError("Django is not installed. Install with: pip install mailchk[django]")
    
    # Try Django settings first
    if hasattr(settings, 'MAILCHK_API_KEY'):
        config = {
            'api_key': settings.MAILCHK_API_KEY,
        }
        
        if hasattr(settings, 'MAILCHK_BASE_URL'):
            config['base_url'] = settings.MAILCHK_BASE_URL
            
        if hasattr(settings, 'MAILCHK_TIMEOUT'):
            config['timeout'] = settings.MAILCHK_TIMEOUT
            
        return Mailchk(**config)
    
    # Fall back to environment variables
    elif getattr(settings, 'MAILCHK_AUTO_CONFIGURE', True):
        try:
            config = from_environment()
            return Mailchk(**config)
        except AuthenticationError:
            pass
    
    raise AuthenticationError(
        "No Mailchk configuration found. Set MAILCHK_API_KEY in Django settings "
        "or configure environment variables."
    )


class EmailValidationField(EmailField):
    """
    Django form field that validates emails using Mailchk.
    
    Example:
        >>> from mailchk.django_integration import EmailValidationField
        >>> from django import forms
        >>> 
        >>> class SignupForm(forms.Form):
        ...     email = EmailValidationField(
        ...         allow_disposable=False,
        ...         min_deliverability=70
        ...     )
    """
    
    def __init__(
        self,
        *args,
        allow_disposable: bool = True,
        allow_free_email: bool = True,
        min_deliverability: int = 50,
        max_risk_level: str = "critical",
        client: Optional[Mailchk] = None,
        **kwargs
    ):
        """
        Initialize the email validation field.
        
        Args:
            allow_disposable: Allow disposable/temporary emails
            allow_free_email: Allow free email providers (Gmail, Yahoo, etc.)
            min_deliverability: Minimum deliverability score (0-100)
            max_risk_level: Maximum allowed risk level (low, medium, high, critical)
            client: Optional Mailchk client instance
        """
        super().__init__(*args, **kwargs)
        self.allow_disposable = allow_disposable
        self.allow_free_email = allow_free_email
        self.min_deliverability = min_deliverability
        self.max_risk_level = max_risk_level
        self.client = client
        
        # Risk level ordering
        self._risk_levels = ["low", "medium", "high", "critical"]
    
    def validate(self, value: Any) -> None:
        """Validate the email using Mailchk."""
        # Run Django's built-in email validation first
        super().validate(value)
        
        if not value:
            return
        
        try:
            client = self.client or get_django_client()
            result = client.validate(value)
            
            # Check if email is valid
            if not result.valid:
                raise DjangoValidationError(
                    result.reason or "Email address is not valid.",
                    code='invalid_email'
                )
            
            # Check disposable email policy
            if not self.allow_disposable and result.disposable:
                raise DjangoValidationError(
                    "Disposable email addresses are not allowed.",
                    code='disposable_email'
                )
            
            # Check free email policy
            if not self.allow_free_email and result.free_email:
                raise DjangoValidationError(
                    "Please use your work email address.",
                    code='free_email'
                )
            
            # Check deliverability threshold
            if result.deliverability_score < self.min_deliverability:
                raise DjangoValidationError(
                    f"Email deliverability score ({result.deliverability_score}) "
                    f"is below required threshold ({self.min_deliverability}).",
                    code='low_deliverability'
                )
            
            # Check risk level
            max_risk_index = self._risk_levels.index(self.max_risk_level)
            current_risk_index = self._risk_levels.index(result.risk_score)
            
            if current_risk_index > max_risk_index:
                raise DjangoValidationError(
                    f"Email has high risk factors: {', '.join(result.risk_factors)}",
                    code='high_risk'
                )
            
            # Check for scam domains
            if result.scam_domain:
                raise DjangoValidationError(
                    "This domain is flagged as suspicious.",
                    code='scam_domain'
                )
        
        except MailchkError as e:
            # Re-raise Mailchk errors as Django validation errors
            raise DjangoValidationError(
                f"Email validation failed: {e.message}",
                code='validation_error'
            )


class BusinessEmailField(EmailValidationField):
    """
    Django form field for business emails (no free providers, no disposable).
    
    Example:
        >>> class EnterpriseSignupForm(forms.Form):
        ...     work_email = BusinessEmailField(min_deliverability=80)
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('allow_disposable', False)
        kwargs.setdefault('allow_free_email', False)
        kwargs.setdefault('min_deliverability', 70)
        kwargs.setdefault('max_risk_level', 'medium')
        super().__init__(*args, **kwargs)


# Django Admin integration
if DJANGO_AVAILABLE and admin:
    class EmailValidationMixin:
        """
        Mixin for Django admin to add email validation actions.
        
        Example:
            >>> from django.contrib import admin
            >>> from mailchk.django_integration import EmailValidationMixin
            >>> 
            >>> @admin.register(User)
            >>> class UserAdmin(EmailValidationMixin, admin.ModelAdmin):
            ...     list_display = ['email', 'is_active']
            ...     actions = ['validate_emails']
        """
        
        def validate_emails(self, request, queryset):
            """Admin action to validate selected users' emails."""
            try:
                client = get_django_client()
                updated = 0
                
                for obj in queryset:
                    if hasattr(obj, 'email') and obj.email:
                        try:
                            result = client.validate(obj.email)
                            
                            # Update object with validation results if fields exist
                            if hasattr(obj, 'email_valid'):
                                obj.email_valid = result.valid
                            if hasattr(obj, 'email_disposable'):
                                obj.email_disposable = result.disposable
                            if hasattr(obj, 'email_risk_score'):
                                obj.email_risk_score = result.risk_score
                            if hasattr(obj, 'email_deliverability'):
                                obj.email_deliverability = result.deliverability_score
                            
                            obj.save(update_fields=[
                                f for f in ['email_valid', 'email_disposable', 
                                          'email_risk_score', 'email_deliverability']
                                if hasattr(obj, f)
                            ])
                            updated += 1
                            
                        except MailchkError:
                            continue  # Skip failed validations
                
                self.message_user(
                    request,
                    f"Successfully validated {updated} email addresses."
                )
                
            except AuthenticationError:
                self.message_user(
                    request,
                    "Mailchk not configured. Check your API key.",
                    level='ERROR'
                )
        
        validate_emails.short_description = "Validate selected email addresses"


# Django management command
def create_management_command():
    """
    Create a Django management command for email validation.
    
    Save this as: management/commands/validate_emails.py
    """
    if not DJANGO_AVAILABLE:
        return None
    
    from django.core.management.base import BaseCommand
    from django.apps import apps
    
    class Command(BaseCommand):
        help = 'Validate email addresses in your database'
        
        def add_arguments(self, parser):
            parser.add_argument(
                '--model',
                required=True,
                help='Model to validate (format: app_label.ModelName)'
            )
            parser.add_argument(
                '--email-field',
                default='email',
                help='Name of the email field (default: email)'
            )
            parser.add_argument(
                '--batch-size',
                type=int,
                default=100,
                help='Number of records to process at once'
            )
            parser.add_argument(
                '--dry-run',
                action='store_true',
                help='Show what would be validated without making changes'
            )
        
        def handle(self, *args, **options):
            try:
                app_label, model_name = options['model'].split('.')
                Model = apps.get_model(app_label, model_name)
            except (ValueError, LookupError):
                self.stderr.write(
                    self.style.ERROR(f"Invalid model: {options['model']}")
                )
                return
            
            email_field = options['email_field']
            if not hasattr(Model, email_field):
                self.stderr.write(
                    self.style.ERROR(f"Model {Model} has no field '{email_field}'")
                )
                return
            
            try:
                client = get_django_client()
            except AuthenticationError as e:
                self.stderr.write(self.style.ERROR(str(e)))
                return
            
            queryset = Model.objects.exclude(**{f"{email_field}__isnull": True})
            total = queryset.count()
            
            if options['dry_run']:
                self.stdout.write(
                    f"Would validate {total} email addresses in {Model._meta.label}"
                )
                return
            
            self.stdout.write(f"Validating {total} email addresses...")
            
            validated = 0
            for obj in queryset.iterator(chunk_size=options['batch_size']):
                email = getattr(obj, email_field)
                if email:
                    try:
                        result = client.validate(email)
                        # Update object with results if additional fields exist
                        # This would need to be customized based on your model
                        validated += 1
                    except MailchkError:
                        continue
            
            self.stdout.write(
                self.style.SUCCESS(f"Successfully validated {validated} emails")
            )
    
    return Command