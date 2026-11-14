"""Unified JSON error responses: Persian `detail` + machine-readable `code`."""
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler

from config import messages as msgs
from config.messages import error_messages


class NotFound(APIException):
    """Object missing or belonging to another user: always 404, never 403."""

    status_code = 404

    def __init__(self):
        super().__init__({"detail": msgs.PERSIAN_ERRORS[msgs.NOT_FOUND], "code": msgs.NOT_FOUND})


def _first_string(value):
    """Pull the first human-readable string out of nested DRF error structures."""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        for item in value:
            result = _first_string(item)
            if result:
                return result
    elif isinstance(value, dict):
        for key in ("detail", "code", "error"):
            if key in value:
                result = _first_string(value[key])
                if result:
                    return result
    return None


def _find_detail_code(data):
    """Locate a {"detail": ..., "code": ...} pair nested anywhere in the errors."""
    if isinstance(data, dict):
        if "detail" in data and data.get("code") and _first_string(data.get("detail")):
            return data
        for value in data.values():
            found = _find_detail_code(value)
            if found:
                return found
    elif isinstance(data, (list, tuple)):
        for item in data:
            found = _find_detail_code(item)
            if found:
                return found
    return None


def _translate(detail):
    """Map known English DRF detail strings to Persian messages."""
    if isinstance(detail, str) and detail in error_messages:
        return error_messages[detail]
    if isinstance(detail, list):
        return [_translate(item) for item in detail]
    if isinstance(detail, dict):
        return {key: _translate(value) for key, value in detail.items()}
    return detail


def _pick_code(data):
    """Find a machine-readable error code anywhere in the error structure."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "code" and isinstance(value, str):
                return value
            if isinstance(value, (list, dict, tuple)):
                code = _pick_code(value)
                if code:
                    return code
    elif isinstance(data, (list, tuple)):
        for item in data:
            code = _pick_code(item)
            if code:
                return code
    return None


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    code = None
    exc_code = getattr(exc, "code", None)
    if isinstance(exc_code, str):
        code = exc_code

    data = response.data

    # Views/serializers may raise {"detail": ..., "code": ...} pairs, possibly
    # wrapped by a field name. Normalize them to the flat target shape.
    found = _find_detail_code(data) if isinstance(data, dict) else None
    if found:
        detail_str = _first_string(found["detail"])
        code_str = _first_string(found["code"])
        if detail_str:
            payload = {"detail": detail_str}
            resolved_code = code_str or code
            if resolved_code:
                payload["code"] = resolved_code
            response.data = payload
            return response

    if code is None and isinstance(data, dict):
        code = _pick_code(data)

    response.data = {"detail": _translate(data)}
    if code:
        response.data["code"] = code
    return response
