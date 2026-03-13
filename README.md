# bodepontoio
Toolbox da Bode.io para projetos em Django
# django-bodepontoio

Toolbox da Bode.io para projetos em Django — JWT authentication, utility models, helpers and services.

## Features

- Custom `User` model with email as the unique identifier (no username)
- JWT authentication via `djangorestframework-simplejwt`
- DRF endpoints: login, logout, register, password change, password reset request/confirm, e-mail confirmation and Google social login
- Abstract base models: `BaseModel` (timestamps) and `LogicDeletable` (soft deletion)
- Built-in models: `Pais`, `LoginRecord`, `ConsultaCEP`, `OptimizedImageWithTinyPNG`
- CEP lookup service with ViaCEP / AwesomeAPI fallback and database caching
- Login tracking via Django signals
- Utility functions: file cleaners, date/string/number formatters, workday calculator, email obfuscation, MX-validating form field, PBKDF2 hashing, pagination fix, MySQL `ROUND`
- Template tags: `grana` (R$ formatting), `multiply`, `roi`, `url_replace`
- Sentry metrics helpers (optional)
- Management commands: country import, TinyPNG image compression
- Standardized success and error responses across all endpoints

## Installation

```bash
pip install git+https://github.com/bodedev/bodepontoio.git@matheus
```

Optional extras:

```bash
pip install "django-bodepontoio[tinify]"   # TinyPNG image compression
pip install "django-bodepontoio[sentry]"   # Sentry metrics helpers
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
BODEPONTOIO = {
    "FRONTEND_URL": "https://app.example.com",           # default: "http://localhost:3000"
    "PASSWORD_RESET_URL_PATH": "/reset/{uid}/{token}/",  # default: "/reset-password/{uid}/{token}/"
    "GOOGLE_CLIENT_ID": "your-client-id.apps.googleusercontent.com",  # required for Google login
}
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
| POST | `register/` | Public | Create account, sends confirmation email |
| POST | `password/change/` | Authenticated | Change password |
| POST | `password/reset/` | Public | Request reset email |
| POST | `password/reset/confirm/` | Public | Confirm reset with uid + token |
| GET | `email/confirm/<uid>/<token>/` | Public | Confirm email address |
| POST | `email/confirm/resend/` | Public | Re-send confirmation email |
| POST | `social/google/` | Public | Login or register via Google ID token |

## Email Confirmation

When a user registers, a confirmation email is sent automatically. **Login is blocked until the email address is confirmed.**

### Flow

1. User registers → confirmation email sent
2. User clicks the link in the email → `GET email/confirm/<uid>/<token>/` → account activated
3. User can now log in

### Resend

`POST email/confirm/resend/` accepts `{"email": "..."}`. It silently does nothing if the address is unknown or already confirmed (anti-enumeration).

### Customising the template

**Django template override** (no config needed): create a file at the same path inside any directory listed in `TEMPLATES[0]['DIRS']`:

```
your_project/
  templates/
    bodepontoio/
      email_confirmation_email.html
```

### Template context

| Variable | Description |
|---|---|
| `user` | The `User` instance |
| `confirm_url` | Full confirmation URL |

## Password Reset Email

A styled HTML email (with plain-text fallback) is sent automatically when a user requests a password reset.

### Customising the template

**Django template override** (no config needed): create a file at the same path inside any directory listed in `TEMPLATES[0]['DIRS']`:

```
your_project/
  templates/
    bodepontoio/
      password_reset_email.html
```

### Template context

| Variable | Description |
|---|---|
| `user` | The `User` instance requesting the reset |
| `reset_url` | Full URL the user should click to reset their password |

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
        {"field": "email", "message": "Este campo é obrigatório."},
        {"field": "non_field_errors", "message": "Credenciais inválidas."}
    ]
}
```

**All other errors**:
```json
{
    "success": false,
    "type": "authentication_error",
    "error": "As credenciais de autenticação não foram fornecidas."
}
```

Possible `type` values:
- `validation_error`
- `authentication_error`
- `permission_error`
- `not_found`
- `parse_error`
- `method_not_allowed`
- `not_acceptable`
- `unsupported_media_type`
- `throttled`

Unknown exception types fall back to the class name in `snake_case`.

## Base Models

```python
from bodepontoio.models import BaseModel, LogicDeletable

class Invoice(LogicDeletable):
    ...
```

### BaseModel

Adds `created` and `updated` (both `DateTimeField`, auto-managed) to any model.

### LogicDeletable

Extends `BaseModel` with soft deletion. Fields added: `excluido` (bool), `excluido_em` (datetime), `excluido_por` (FK to `AUTH_USER_MODEL`, nullable).

```python
# Querying
Invoice.objects.all()             # live rows only (default manager)
Invoice.com_excluidos.all()       # includes soft-deleted rows

# Instance operations
invoice.delete()                  # soft delete (excluido=True, excluido_em=now)
invoice.logic_delete(user)        # soft delete, records who did it in excluido_por
invoice.reativar()                # undo — clears excluido, excluido_em, excluido_por
```

## Built-in Models

### Pais

Country model with 195 pre-loaded entries (see [Management Commands](#management-commands)).

| Field | Type |
|-------|------|
| `nome` | CharField (unique) |
| `capital` | CharField |
| `codigo_3` | CharField (unique, 3-letter ISO) |
| `codigo_2` | CharField (unique, 2-letter ISO) |

### LoginRecord

Automatically created on every `user_logged_in` signal via a built-in signal handler. Tracks the user and their IP address.

| Field | Type |
|-------|------|
| `user` | FK to `AUTH_USER_MODEL` (nullable) |
| `ip` | GenericIPAddressField |

### ConsultaCEP

Cache for CEP lookups. Populated automatically by the [CEP Service](#cep-service).

| Field | Type |
|-------|------|
| `cep` | CharField (unique, formatted `XXXXX-XXX`) |
| `logradouro` | CharField |
| `complemento` | CharField |
| `bairro` | CharField |
| `localidade` | CharField |
| `uf` | CharField |
| `ibge` | CharField |
| `ddd` | CharField |
| `localidade_slug` | SlugField (auto-generated) |
| `fonte` | CharField (`viacep` or `awesomeapi`) |

### OptimizedImageWithTinyPNG

Tracks images compressed by the `compress_images_with_tinify` command. Inherits `LogicDeletable`.

| Field | Type |
|-------|------|
| `path` | CharField |

## CEP Service

Looks up Brazilian postal codes with automatic fallback and database caching.

```python
from bodepontoio.services.cep_service import cep_service

dados = cep_service.consultar("01001-000")
# DadosCEP(cep='01001-000', localidade='São Paulo', uf='SP', ...)

# Search cached CEPs by city slug
resultados = cep_service.buscar_por_slug("sao-paulo")
```

Lookup order:
1. Local database cache (`ConsultaCEP`)
2. ViaCEP API
3. AwesomeAPI (fallback)

Results are saved to the database automatically for future lookups.

Exceptions:
- `CEPInvalidoError` — malformed CEP
- `CEPNaoEncontradoError` — not found in any provider

## Utilities

All utilities live under `bodepontoio.utils`.

### cleaners

```python
from bodepontoio.utils.cleaners import (
    file_name_cleaner,    # slugify filename, preserve extension
    file_extension,       # extract file extension
    extract_name_and_surname,  # split "João Silva" → ("João", "Silva")
    get_client_ip,        # extract IP from request (X-Forwarded-For aware)
)
```

### strings

```python
from bodepontoio.utils.strings import trim_string
trim_string("  hello   world  ")  # "hello world"
```

### dates

```python
from bodepontoio.utils.dates import month_to_string
month_to_string(3)  # "Março"
```

### numbers

```python
from bodepontoio.utils.numbers import grana
grana(1234.56)              # "1.234,56"
grana(1000, prefixo="R$")  # "R$ 1.000,00"
```

### workdays

Brazilian workday calculator with holidays from 2023 to 2028.

```python
from bodepontoio.utils.workdays import workday, num_workdays

workday(start_date, 5)              # 5 business days forward
num_workdays(start_date, end_date)  # count business days in range
```

### email.ofuscate

```python
from bodepontoio.utils.email.ofuscate import obfuscate_email
obfuscate_email("user@gmail.com")  # "us**@g****.com"
```

### forms.fields

```python
from bodepontoio.utils.forms.fields import ValidatingEmailField
# Django form field that checks MX records (requires dnspython)
```

### pagination

```python
from bodepontoio.utils.pagination import LastPageFixPaginator
# Paginator that returns the last page instead of raising EmptyPage
```

### database.mysql

```python
from bodepontoio.utils.database.mysql import Round
# Django Func for ROUND(expr, 2)
```

### passwords.generate_hash

```python
from bodepontoio.utils.passwords.generate_hash import (
    hash_password_pbkdf2,     # returns "pbkdf2$iterations$salt_hex$hash_hex"
    verify_password_pbkdf2,   # constant-time verification
)
```

## Template Tags

```html
{% load bodepontoio_tags %}

{{ valor|grana }}           {# 1.234,56 #}
{{ valor|grana:"R$" }}      {# R$ 1.234,56 #}
{{ valor|multiply:2 }}      {# valor * 2 #}
{{ valor|roi:custo }}       {# ((valor - custo) / custo) * 100 #}
{% url_replace request "page" 2 %}  {# preserves other query params #}
```

## Metrics

Optional Sentry metrics wrappers. Requires `sentry-sdk` (`pip install "django-bodepontoio[sentry]"`).

```python
from bodepontoio.metrics import count, distribution, gauge

count("my_event")
distribution("response_time", 0.45, unit="second")
gauge("queue_size", 42)
```

All calls are wrapped in try/except — they silently log errors if Sentry is unavailable.

## Management Commands

### bpio_importar_paises

Imports 195 countries from the bundled `paises.csv` into the `Pais` model.

```bash
python manage.py bpio_importar_paises
```

### compress_images_with_tinify

Compresses images larger than 250 KB using TinyPNG. Requires `TINYPNG_KEY` in settings and the `tinify` extra.

```bash
pip install "django-bodepontoio[tinify]"
python manage.py compress_images_with_tinify --folders media/uploads/
```

Already-compressed images are tracked in `OptimizedImageWithTinyPNG` and skipped on subsequent runs.
