import re
from typing import Dict, List, Any


def extract_key_value(text: str, config: Dict[str, Any]) -> str:
    """
    Finds a value associated with a specified key pattern in the text.

    This method is designed to find structured data like "Key: Value" or
    "Key - Value" within the email body. It accepts multiple key patterns.

    Args:
        text: The clean plaintext email body.
        config: A dictionary containing parsing instructions.
                Expected keys: 'key_patterns' (List[str]), 'delimiter' (str).

    Returns:
        The extracted value as a string, or an empty string if not found.
    """
    # Use explicit type annotation for local variable for clarity
    key_patterns: List[str] = config.get("key_patterns", [])

    # Escape special regex characters in the delimiter (e.g., if delimiter is '$' or '.')
    delimiter: str = re.escape(config.get("delimiter", ":"))

    if not text or not key_patterns:
        return ""

    # 1. Prepare key patterns for combined regex
    # Escape key patterns as they might contain regex-sensitive characters (like parentheses)
    escaped_patterns = [re.escape(k.strip()) for k in key_patterns if k.strip()]
    if not escaped_patterns:
        return ""

    # 2. Construct the full pattern:
    # (?:{'|'.join(...)}) : Non-capturing group for all possible escaped key patterns
    # \s* : Zero or more whitespace characters
    # {delimiter}           : The escaped delimiter (e.g., ':')
    # \s* : Zero or more whitespace characters
    # ((\s*[^,\n\r]+?))    : Capture Group 1 (the value):
    #   - \s* : Optional leading whitespace in the value
    #   - [^,\n\r]+?        : Non-greedy match of one or more characters until a comma, newline, or carriage return
    full_pattern = rf"(?:{'|'.join(escaped_patterns)})\s*{delimiter}\s*((\s*[^,\n\r]+?))"

    # re.IGNORECASE makes the key match case-insensitive
    match = re.search(full_pattern, text, re.IGNORECASE)

    if match:
        # Return the content of the outermost capture group (group 1), stripped of leading/trailing whitespace
        return match.group(1).strip()

    return ""


def extract_regex_pattern(text: str, config: Dict[str, Any]) -> str:
    """
    Extracts a value using a custom, full regular expression pattern defined in the config.

    This method is suitable for complex extraction logic where a simple key-value
    search is insufficient (e.g., extracting URLs, specific formatted codes).

    Args:
        text: The clean plaintext email body.
        config: A dictionary containing parsing instructions.
                Expected key: 'pattern' (str) containing at least one capture group.

    Returns:
        The extracted value from the first capture group, or an empty string.
    """
    pattern: str = config.get("pattern", "")

    if not text or not pattern:
        return ""

    try:
        # re.IGNORECASE: case-insensitive matching
        # re.DOTALL: makes '.' match newlines, useful for multiline extraction
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        # Check if a match was found and if it contains capture groups
        if match and match.groups():
            # Return the content of the first capture group (group 1)
            return match.group(1).strip()
    except re.error as e:
        # Log or handle invalid regex patterns gracefully
        logger.error(f"Unexpected error extracting regex pattern from {text}: {e}")

    return ""