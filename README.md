# django-bodepontoio

A reusable Django app providing JWT authentication with an email-based custom User model.

## Features

- Custom `User` model with email as the unique identifier (no username)
- JWT authentication via `djangorestframework-simplejwt`
- Six DRF endpoints: login, logout, register, password change, password reset request, password reset confirm
- Abstract base models: `TimeStampedModel` (timestamps) and `SoftDeleteModel` (soft deletion)
- Standardized success and error responses across all endpoints

## Installation

```bash
pip install git+https://github.com/your-org/bodepontoio.git@v0.1.0
```

## Setup

```python
# settings.py
INSTALLED_APPS = [
    ...
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # required for LogoutView
    "bodepontoio",
]
AUTH_USER_MODEL = "bodepontoio.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "bodepontoio.exceptions.exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["bodepontoio.renderers.SuccessJSONRenderer"],
}

SIMPLE_JWT = {
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# Optional bodepontoio overrides
BODEPONTOIO = {"FRONTEND_URL": "https://app.example.com"}
```

```python
# urls.py
path("api/auth/", include("bodepontoio.urls", namespace="bodepontoio")),
```

```bash
python manage.py migrate
```

## Endpoints

| Method | URL | Permission | Description |
|--------|-----|------------|-------------|
| POST | `login/` | Public | Obtain access + refresh tokens |
| POST | `logout/` | Authenticated | Blacklist refresh token |
| POST | `register/` | Public | Create account, returns tokens |
| POST | `password/change/` | Authenticated | Change password |
| POST | `password/reset/` | Public | Request reset email |
| POST | `password/reset/confirm/` | Public | Confirm reset with uid + token |

## Responses

All responses share a consistent envelope.

**Success**:
```json
{
    "success": true,
    "data": { ... }
}
```

**Success — empty body** (e.g. logout):
```json
{
    "success": true
}
```

**Success — paginated list**:
```json
{
    "success": true,
    "count": 20,
    "next": "http://example.com?page=2",
    "previous": null,
    "data": [ ... ]
}
```

**Validation error** (HTTP 400):
```json
{
    "success": false,
    "type": "validation_error",
    "errors": [
        {"field": "email", "message": "This field is required."},
        {"field": "non_field_errors", "message": "Invalid credentials."}
    ]
}
```

**All other errors**:
```json
{
    "success": false,
    "type": "authentication_error",
    "error": "Authentication credentials were not provided."
}
```

Possible `type` values:
- `validation_error`
- `authentication_error`
- `permission_error`,
- `not_found`
- `parse_error`
- `method_not_allowed`
- `not_acceptable`
- `unsupported_media_type`
- `throttled`

Unknown exception types fall back to the class name in `snake_case`.

## Base Models

```python
from bodepontoio.models import TimeStampedModel, SoftDeleteModel

class Invoice(SoftDeleteModel):
    ...
```

### TimeStampedModel

Adds `created_at` and `updated_at` to any model.

### SoftDeleteModel

Extends `TimeStampedModel` with soft deletion. Fields added: `deleted_at`, `deleted_by` (FK to `AUTH_USER_MODEL`, nullable).

```python
# Querying
Invoice.objects.all()             # live rows only (default manager)
Invoice.all_objects.all()         # includes soft-deleted
Invoice.all_objects.alive()       # live rows
Invoice.all_objects.dead()        # soft-deleted rows only

# Instance operations
invoice.delete()                  # soft delete, deleted_by=None
invoice.delete(deleted_by=user)   # soft delete, records who did it
invoice.restore()                 # undo — clears deleted_at and deleted_by
invoice.hard_delete()             # permanent delete
invoice.is_deleted                # True if deleted_at is set

# Bulk operations
Invoice.objects.filter(...).delete(deleted_by=user)  # bulk soft delete
Invoice.all_objects.hard_delete()                     # bulk permanent delete
```
