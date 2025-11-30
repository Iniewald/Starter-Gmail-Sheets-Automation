"""
Configuration settings for the Email Processor application.

This module loads environment variables from a .env file (via `env_manager.py`)
and defines default values, API constants, and the essential PARSING_MAP
structure used to extract specific data fields from emails.
"""
import os
from typing import List, Dict, Any, Final
from env_manager import load_environment

# Load environment variables immediately upon module import
load_environment()

# --- Google API and Application Constants ---

# File path for the downloaded OAuth 2.0 client secrets
CLIENT_SECRET_FILE: Final[str] = os.getenv("CLIENT_SECRET_FILE", "client_secret.json")

# Google Sheet information
SPREADSHEET_ID: Final[str] = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME: Final[str] = os.getenv("SHEET_NAME", "Emails")

# Gmail/Processing settings
MAX_RESULTS: Final[int] = int(os.getenv("MAX_RESULTS", 10))
HIGH_PRIORITY_KEYWORDS: Final[str] = os.getenv("HIGH_PRIORITY_KEYWORDS", "")

# The query used to filter which messages are fetched by Gmail API
GMAIL_SEARCH_QUERY: Final[str] = os.getenv("GMAIL_SEARCH_QUERY", "is:unread")

# Credentials file path
TOKEN_PICKLE: Final[str] = os.getenv("TOKEN_PICKLE", "token.pickle")

# OAuth 2.0 Scopes (must be a list of strings)
SCOPES: Final[List[str]] = ["https://www.googleapis.com/auth/gmail.modify","https://www.googleapis.com/auth/spreadsheets"]

# Logging level
LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")


# --- Data Extraction Mapping ---

# Defines how specific fields should be extracted from the email content.
# Each dictionary represents a rule:
# - output_field: The key used in the final parsed data dictionary and in the Sheet header.
# - method: The parsing technique ('key_value', 'regex_pattern', or 'header').
# - Additional fields are specific to the method (e.g., 'key_patterns', 'pattern', 'header_name').
PARSING_MAP: Final[List[Dict[str, Any]]] = [
    # --- 1. Key-Value Fields (Relies on stable 'extract_key_value') ---
    # These fields must be clearly labeled in the body.
    {
        "output_field": "Order Status",
        "method": "key_value",
        "key_patterns": ["Status", "Order Status", "State"],
        "delimiter": r"\s*[:\-\#]\s*",
    },
    {
        "output_field": "Total Amount",
        "method": "key_value",
        "key_patterns": ["Total", "Total Amount", "Total Amount Due", "Invoice Total"],
        "delimiter": r"\s*[:\-\#]\s*",
    },
    {
        "output_field": "Shipping Method",
        "method": "key_value",
        "key_patterns": ["Shipping Method", "Ship Method"],
        "delimiter": r"\s*[:\-\#]\s*",
    },
    {
        "output_field": "Order ID",
        "method": "key_value",
        "key_patterns": ["Order ID", "Order-ID"],
        "delimiter": r"\s*[:\-\#]\s*",
    },

    # --- 2. Simple Regex Field (For common pattern data) ---
    # Captures a simple date/time stamp if found outside the headers.
    {
        "output_field": "Invoice Date",
        "method": "regex_pattern",
        # Matches common date formats like YYYY-MM-DD or MM/DD/YYYY
        "pattern": r"Date\s*:\s*(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    },
]