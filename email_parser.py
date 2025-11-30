from base64 import urlsafe_b64decode
import re
from typing import Dict, List, Any, Optional
from parsing_tools import extract_key_value, extract_regex_pattern

from utils.logger import setup_logger
import config

logger = setup_logger(__name__)


def safe_b64_decode(data: Optional[str]) -> str:
    """
    Decodes a URL-safe Base64 encoded string, handling padding issues and decoding errors.

    Args:
        data: The Base64 encoded string, typically from a Gmail message body part.

    Returns:
        The decoded UTF-8 string, or an empty string if decoding fails or data is empty.
    """
    if not data:
        return ''
    try:
        # Gmail uses URL-safe Base64 encoding which might omit standard padding ('=')
        padding = len(data) % 4
        if padding:
            data += "=" * (4 - padding)

        # Use 'replace' error handler for robust decoding of potentially bad input
        return urlsafe_b64decode(data).decode("utf-8", errors="replace")
    except Exception as e:
        logger.error("Failed to decode base64 encoded data: %s", e)
        return ''


def strip_html(html: Optional[str]) -> str:
    """
    Converts HTML content into clean plaintext, handling common formatting elements.

    Args:
        html: The HTML string to be cleaned.

    Returns:
        The cleaned plaintext string.
    """
    if not html:
        return ''

    # 1. Remove script and style tags (case-insensitive, including content)
    html = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", "", html)

    # 2. Replace structural tags with newlines for better paragraph breaks
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p>", "\n", html)

    # 3. Remove all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", html)

    # 4. Collapse multiple whitespace characters (including newlines from step 2) into a single space, then strip
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_text_body(payload: Dict) -> str:
    """
    Recursively searches the message payload for the best available plaintext body.

    Prioritizes:
    1. text/plain part (returns immediately)
    2. text/html part (strips HTML and returns)
    3. Searches nested parts recursively.

    Args:
        payload: The 'payload' dictionary from the full Gmail message object.

    Returns:
        The clean plaintext body content, or an empty string if none is found.
    """
    if not payload:
        return ''

    # Handle the case where the payload itself is a text part
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return safe_b64_decode(data)

    parts: List[Dict] = payload.get('parts', [])
    for part in parts:
        p_mime = part.get('mimeType', "")

        # Strategy 1: Find and prioritize the text/plain part
        if p_mime == 'text/plain':
            data = part.get('body', {}).get('data', "")
            if data:
                return safe_b64_decode(data)

        # Strategy 2: If no plaintext, fallback to text/html and strip tags
        if p_mime == 'text/html':
            data = part.get('body', {}).get('data', "")
            if data:
                return strip_html(safe_b64_decode(data))

        # Strategy 3: Handle nested messages (e.g., attachments or alternative views)
        if part.get("parts"):
            nested = extract_text_body(part)
            if nested:
                return nested

    # Final attempt: check the main body if it has data but was missed above
    data = payload.get('body', {}).get('data', "")
    if data:
        return safe_b64_decode(data)

    return ""


def get_header(headers: List[Dict], name: str) -> str:
    """
    Retrieves the value of a specific header from the list of headers.

    Args:
        headers: The list of header dictionaries from the message payload.
        name: The name of the header to retrieve (e.g., 'Subject', 'From', 'Date').

    Returns:
        The header value as a string, or an empty string if not found.
    """
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def parse_email(full_message: Dict) -> Dict[str, Any]:
    """
    Parses a full Gmail message object, extracts standard headers/body, and applies
    the custom extraction rules defined in config.PARSING_MAP.

    It also checks the content against HIGH_PRIORITY_KEYWORDS.

    Args:
        full_message: The full message dictionary retrieved from the Gmail API.

    Returns:
        A dictionary containing standard fields (id, subject, date, body, etc.)
        and all custom extracted fields.
    """
    payload = full_message.get("payload", {})
    headers: List[Dict] = payload.get("headers", [])

    # Extract standard fields
    subject = get_header(headers, "Subject")
    from_raw = get_header(headers, "From")
    date = get_header(headers, "Date")
    body = extract_text_body(payload)

    parsed: Dict[str, Any] = {
        "Message ID": full_message.get("id"),
        "Thread ID": full_message.get("threadId"),
        "Subject": subject,
        "From": from_raw,
        "Date": date,
        "Body (plain)": body,
        "Priority": "Normal",  # Default priority
    }

    # --- Apply Custom Parsing Rules (PARSING_MAP) ---
    for instruction in config.PARSING_MAP:
        output_field = instruction.get("output_field")
        method = instruction.get("method")
        extracted_value = ""

        if method == "header":
            # Extract directly from email headers
            extracted_value = get_header(headers, instruction.get("header_name", ""))

        elif method == "key_value":
            # Extract data using predefined key patterns and delimiters from the body
            extracted_value = extract_key_value(body, instruction)

        elif method == "regex_pattern":
            # Extract data using a custom regular expression from the body
            extracted_value = extract_regex_pattern(body, instruction)

        # Only add the extracted field if a value was actually found
        if extracted_value and output_field:
            parsed[output_field] = extracted_value

    # --- Priority Flagging ---
    combined_content = f"{subject or ''} {body or ''} {from_raw or ''}".lower()
    combined_content = re.sub(r"\s+", " ", combined_content).strip()

    # Split the config string into individual keywords (assuming comma-separated)
    priority_keywords = [kw.strip() for kw in config.HIGH_PRIORITY_KEYWORDS.split(',') if kw.strip()]

    for kw in priority_keywords:
        # Use word boundaries (\b) for precise keyword matching
        pattern = rf"\b{re.escape(kw.lower())}\b"
        if re.search(pattern, combined_content):
            parsed["Priority"] = "High"
            break

    logger.info("Parsed message id=%s, subject='%s', priority=%s",
                parsed["Message ID"], subject[:40] + "..." if len(subject) > 40 else subject, parsed["Priority"])
    return parsed