"""
pipeline.py
------------
The end-to-end runnable script that executes the entire workflow:
1. Authenticate with Google (Gmail and Sheets).
2. Fetch unread emails.
3. Parse structured data from email content.
4. Write parsed data to a Google Sheet.
5. Mark processed emails as read.
"""
import datetime
from typing import Dict, List, Any

from utils.logger import setup_logger

import config
from gmail_services import get_credentials, build_services, fetch_unread_full_emails, mark_as_read
from email_parser import parse_email
from save_to_sheets import ensure_header_row, append_rows

logger = setup_logger(__name__)


def get_final_header() -> List[str]:
    """
    Generates the final header row based on standard fields and custom fields
    defined in the configuration map.
    """
    # 1. Standard (Fixed) Fields
    standard_fields = [
        "Date", "From", "Subject", "Body (plain)",
        "Priority", "Message ID", "Thread ID"
    ]

    # 2. Add custom fields from config.PARSING_MAP
    # This extracts the required output column name for every parsing instruction
    custom_fields = [inst["output_field"] for inst in config.PARSING_MAP]

    return standard_fields + custom_fields


# Define the FINAL_HEADER here so it can be accessed throughout the module
FINAL_HEADER: List[str] = get_final_header()


def build_row(parsed: Dict[str, Any], header: List[str]) -> List[Any]:
    """
    Converts a dictionary of parsed email data into a list (row) of values,
    based on the exact order of the provided header list.

    Args:
        parsed: The dictionary output from parse_email(), includes custom fields.
        header: The full list of column names (Standard + Custom).

    Returns:
        A list of strings/values ready to be appended to the Google Sheet.
    """
    row = []

    for field_name in header:
        # Use .get() with a fallback empty string for robustness (handles missing custom fields)
        value = parsed.get(field_name, "")

        # Apply specific logic for truncation only to the body field
        if field_name == "Body (plain)":
            row.append(str(value)[:10000])
        elif field_name == "Date":
            # Use fallback date if the parsed dictionary is missing the date
            row.append(value or datetime.datetime.utcnow().isoformat())
        else:
            row.append(value)

    return row

def run_pipeline() -> None:
    """
    Executes the entire email processing pipeline.
    """
    # --- Step 1: Authentication and Service Initialization ---
    try:
        creds = get_credentials()
        gmail_service, sheets_service = build_services(creds)
        logger.info("Services initialized successfully.")

    except Exception as e:
        logger.critical("Failed to initialize services and authenticate: %s. Exiting pipeline.", e)
        return

    # --- Step 2: Prepare Sheet Header ---
    try:
        ensure_header_row(sheets_service, header=FINAL_HEADER)
        logger.info("Header row verified/created successfully.")
    except Exception as e:
        logger.error("Failed to verify/create header row: %s. Continuing with data fetch.", e)
    # --- Step 3: Fetch Unread Messages ---
    try:
        messages = fetch_unread_full_emails(gmail_service, max_results=config.MAX_RESULTS)
        logger.info("Fetched %d emails successfully.", len(messages))
        if not messages:
            logger.info("No unread emails found to process. Pipeline complete.")
            return
    except Exception as e:
        logger.error("Failed to fetch messages: %s.", e)
        messages = []
        return

    rows: List[List[Any]] = []
    processed_ids: List[str] = []

    # --- Step 4: Parse Messages and Prepare Rows ---
    for m in messages:
        message_id = m.get("id")
        try:
            parsed = parse_email(m)
            rows.append(build_row(parsed, header=FINAL_HEADER))
            processed_ids.append(parsed.get("id"))
        except Exception as e:
            logger.error("Failed to parse message id=%s: %s", message_id, e)

    # --- Step 5: Write to Sheets ---
    if rows:
        try:
            append_rows(sheets_service, rows)
            logger.info("Successfully saved %d rows to Google Sheets.", len(rows))
        except Exception as e:
            logger.critical("Failed to save to Google Sheets: %s. Data lost for this run.", e)
            # Do not mark as read if we failed to save the data.
            return
    else:
        logger.warning("No rows successfully generated from parsed messages.")
        # No need to mark anything as read if nothing was parsed/saved.
        return

    # --- Step 6: Mark Processed Messages as Read ---
    for mid in processed_ids:
        if mid:
            try:
                mark_as_read(gmail_service, mid)
            except Exception as e:
                # Log the error but continue processing other messages
                logger.error("Failed to mark message %s as read: %s", mid, e)

    logger.info("Pipeline completed successfully for %d emails.", len(processed_ids))


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.critical("Unexpected critical crash in pipeline execution: %s", e)