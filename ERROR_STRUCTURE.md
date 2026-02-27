# Seriazer error response with field errors
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

# Other errors
```json
{
    "success": false,
    "type": "error_type",
    "error": "Error message"
}
```