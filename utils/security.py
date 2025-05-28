import html
import os
import re
import logging
from urllib.parse import unquote

logger = logging.getLogger(__name__)


def _remove_dangerous_patterns(content):
    """
    Helper function to remove common dangerous patterns from content.

    Args:
        content (str): The content to clean

    Returns:
        str: Content with dangerous patterns removed
    """
    if not isinstance(content, str):
        return content

    # Remove javascript: protocols
    content = re.sub(r"javascript:", "", content, flags=re.IGNORECASE)

    # Remove script tags
    content = re.sub(
        r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove event handlers
    content = re.sub(r"on\w+\s*=", "", content, flags=re.IGNORECASE)

    # Remove data: URLs that could contain scripts
    content = re.sub(r"data:[^;]*;[^,]*,", "", content, flags=re.IGNORECASE)

    return content


def _remove_html_tags(content):
    """
    Helper function to remove HTML tags from content.

    Args:
        content (str): The content to clean

    Returns:
        str: Content with HTML tags removed
    """
    if not isinstance(content, str):
        return content

    return re.sub(r"<[^>]*>", "", content)


def _remove_control_characters(content):
    """
    Helper function to remove control characters from content.

    Args:
        content (str): The content to clean

    Returns:
        str: Content with control characters removed
    """
    if not isinstance(content, str):
        return content

    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", content)


def _remove_unicode_injection_payloads(content):
    """
    Helper function to remove unicode injection payloads from content.

    Removes various Unicode characters that can be used for injection attacks:
    - Control characters (C0 and C1 control codes)
    - Right-to-left override characters (used for filename spoofing)
    - Zero-width characters (invisible characters)
    - Byte order marks
    - Other potentially dangerous Unicode characters
    """
    if not isinstance(content, str):
        return content

    # Remove C0 control characters (0x00-0x1F) and DEL (0x7F)
    content = re.sub(r"[\u0000-\u001f\u007f]", "", content)

    # Remove C1 control characters (0x80-0x9F)
    content = re.sub(r"[\u0080-\u009f]", "", content)

    # Remove bidirectional text control characters (used for filename spoofing)
    content = re.sub(r"[\u202a-\u202e]", "", content)  # LRE, RLE, PDF, LRO, RLO
    content = re.sub(r"[\u2066-\u2069]", "", content)  # LRI, RLI, FSI, PDI

    # Remove zero-width characters (invisible characters)
    content = re.sub(r"[\u200b-\u200f]", "", content)  # ZWSP, ZWNJ, ZWJ, LRM, RLM
    content = re.sub(
        r"[\u2028-\u2029]", "", content
    )  # Line separator, paragraph separator
    content = re.sub(r"\ufeff", "", content)  # Byte order mark (BOM)

    # Remove other potentially dangerous Unicode characters
    content = re.sub(r"[\u00ad]", "", content)  # Soft hyphen
    content = re.sub(r"[\u034f]", "", content)  # Combining grapheme joiner
    content = re.sub(r"[\u061c]", "", content)  # Arabic letter mark
    content = re.sub(r"[\u180e]", "", content)  # Mongolian vowel separator

    return content


def _remove_php_code(content):
    """
    Helper function to remove PHP code from content.
    """
    if not isinstance(content, str):
        return content

    return re.sub(r"<\?php", "", content)


def sanitize_string_input(filename):
    """
    Sanitize a filename to prevent path traversal and other security issues.

    Args:
        filename (str): The original filename

    Returns:
        str: A sanitized filename safe for storage
    """
    if not filename:
        return "unnamed_file"

    original_filename = filename

    # URL decode the filename to handle encoded path traversal attempts
    filename = unquote(filename)

    # Escape HTML content
    filename = _escape_html_content(filename)

    # Apply common dangerous pattern removal
    filename = _remove_control_characters(filename)
    filename = _remove_dangerous_patterns(filename)
    filename = _remove_html_tags(filename)
    filename = _remove_unicode_injection_payloads(filename)
    filename = _remove_php_code(filename)

    # Remove path traversal patterns
    filename = re.sub(r"\.\.+", "", filename)  # Remove .. patterns
    filename = re.sub(r"[/\\]", "", filename)  # Remove path separators

    # Remove other dangerous characters
    dangerous_chars = r'[<>:"|?*;&%$=]'
    filename = re.sub(dangerous_chars, "", filename)
    filename = re.sub("--", "", filename)

    # Remove Windows reserved names
    windows_reserved = [
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ]

    name_without_ext = os.path.splitext(filename)[0]
    extension = os.path.splitext(filename)[1]

    if name_without_ext.upper() in windows_reserved:
        name_without_ext = f"safe_{name_without_ext}"

    # Reconstruct filename
    filename = name_without_ext + extension

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Ensure filename is not empty
    if not filename:
        return "unnamed_file"

    # Limit filename length (keeping extension)
    max_length = 255
    if len(filename) > max_length:
        name_part = os.path.splitext(filename)[0]
        ext_part = os.path.splitext(filename)[1]
        max_name_length = max_length - len(ext_part)
        filename = name_part[:max_name_length] + ext_part

    if filename != original_filename:
        logger.warning(
            f"Security: Sanitized filename {original_filename} to {filename}."
        )

    return filename


def _escape_html_content(content):
    """
    Escape HTML content to prevent XSS attacks.

    Args:
        content (str): The content to escape

    Returns:
        str: HTML-escaped content
    """
    if not isinstance(content, str):
        return content

    original_content = content

    # First escape HTML entities
    content = html.escape(content, quote=True)

    if content != original_content:
        logger.warning(
            f"Security: Escaped HTML content {original_content} to {content}."
        )

    return content


def sanitize_metadata(metadata):
    """
    Sanitize metadata dictionary to prevent XSS attacks.

    Args:
        metadata (dict): The metadata dictionary

    Returns:
        dict: Sanitized metadata dictionary
    """
    if not isinstance(metadata, dict):
        return metadata

    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, str):
            sanitized[key] = _escape_html_content(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_metadata(value)
        elif isinstance(value, list):
            sanitized[key] = [
                _escape_html_content(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def sanitize_transformations(transformations):
    """
    Sanitize transformation data to prevent XSS and injection attacks.

    Args:
        transformations (list): List of transformation dictionaries

    Returns:
        list: Sanitized transformation data
    """
    if not isinstance(transformations, list):
        logger.warning("Security: transformations is not a list, rejecting")
        return []

    from image_processor.tasks import TRANSFORMATION_MAP

    # Allowed operations to prevent code injection
    allowed_operations = list(TRANSFORMATION_MAP.keys())

    sanitized_transformations = []

    for transformation in transformations:
        if not isinstance(transformation, dict):
            logger.warning("Security: Invalid transformation format, skipping")
            continue

        sanitized_transformation = {}

        # Sanitize operation field
        operation = transformation.get("operation", "")
        if isinstance(operation, str):
            # Apply common sanitization
            operation = _escape_html_content(operation)
            operation = re.sub(
                r"[^\w-]", "", operation
            )  # Only allow alphanumeric and hyphens

            # Check if operation is in allowed list
            if operation.lower() in allowed_operations:
                sanitized_transformation["operation"] = operation.lower()
            else:
                logger.warning(
                    f"Security: Disallowed operation '{operation}', skipping transformation"
                )
                continue
        else:
            logger.warning("Security: Invalid operation type, skipping transformation")
            continue

        # Sanitize params field
        params = transformation.get("params", {})
        if isinstance(params, dict):
            sanitized_params = {}

            for key, value in params.items():
                # Sanitize parameter keys
                if isinstance(key, str):
                    safe_key = re.sub(
                        r"[^\w_]", "", key
                    )  # Only allow alphanumeric and underscores
                    safe_key = _escape_html_content(safe_key)

                    # Sanitize parameter values
                    if isinstance(value, str):
                        safe_value = _escape_html_content(value)
                        sanitized_params[safe_key] = safe_value
                    elif isinstance(value, (int, float)):
                        # Validate numeric parameters are within reasonable bounds
                        if -10000 <= value <= 10000:
                            sanitized_params[safe_key] = value
                        else:
                            logger.warning(
                                f"Security: Parameter value {value} out of bounds, "
                                "setting to 0"
                            )
                            sanitized_params[safe_key] = 0
                    else:
                        logger.warning(
                            f"Security: Unsupported parameter type for {key}, skipping"
                        )

            sanitized_transformation["params"] = sanitized_params
        else:
            logger.warning("Security: Invalid params type, setting empty params")
            sanitized_transformation["params"] = {}

        sanitized_transformations.append(sanitized_transformation)

    return sanitized_transformations
