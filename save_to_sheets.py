from typing import List, Any, Dict, Optional
from googleapiclient.errors import HttpError
import time

from utils.logger import setup_logger
import config

logger = setup_logger(__name__)

_INITIAL_BACKOFF = 1.0  # seconds
_MAX_ATTEMPTS = 5


def ensure_header_row(sheets_service: object, header: List[str],
                      spreadsheet_id: str = config.SPREADSHEET_ID,
                      sheet_name: str = config.SHEET_NAME) -> None:
    """
    Checks if the first row of the Google Sheet contains a header. If the row is
    empty, the predefined header row is written. If an existing header is found
    that DOES NOT MATCH the required header, an error is raised to prevent data misalignment.

    Args:
        sheets_service: The initialized Google Sheets API service object.
        header: The list of required header column names based on PARSING_MAP.
        spreadsheet_id: The ID of the target Google Sheet document.
        sheet_name: The name of the specific sheet/tab within the document.

    Raises:
        ValueError: If a mismatched header is detected.
        HttpError: If the API request fails persistently.
    """
    range_name = f"{sheet_name}!A1:Z1"
    attempt = 0

    while True:
        try:
            # 1. Try to read the first row
            resp: Dict[str, Any] = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                majorDimension="ROWS"
            ).execute()

            values: List[List[str]] = resp.get("values", [])

            if values and values[0]:
                # Clean and filter the existing header for comparison
                existing_header = [cell.strip() for cell in values[0] if cell.strip()]

                # Check if the existing header matches the expected header up to the columns present
                if existing_header == header[:len(existing_header)]:
                    logger.debug("Header already exists and matches expected format in sheet %s.", sheet_name)
                    return
                else:
                    # Mismatch detected. Stop execution.
                    logger.error(
                        "Existing header in sheet '%s' does not match the required schema. "
                        "Expected: %s | Found: %s. Please clear the first row manually.",
                        sheet_name, header, existing_header
                    )
                    raise ValueError("Mismatched Google Sheet header detected. Script aborted.")

            # 2. Write the header if the first row is completely empty or missing
            header_row: List[List[str]] = [header]
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": header_row}
            ).execute()
            logger.info("Wrote standard header row to sheet %s", sheet_name)
            return

        except HttpError as e:
            attempt += 1
            # Check for rate limits or server errors for retries
            if e.resp.status in (429, 500, 503) and attempt < _MAX_ATTEMPTS:
                delay = _INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    f"HttpError writing header (attempt {attempt}): {e.resp.status}. Retrying in {delay:.1f}s"
                )
                time.sleep(delay)
                continue
            else:
                logger.error(f"HttpError: Failed to ensure header row after retries on sheet {sheet_name}: {e}")
                # Re-raise the exception after exhausting retries
                raise
        except ValueError:
            # Re-raise the ValueError exception if it originated from the mismatch check
            raise
        except Exception as e:
            logger.error(f"Unexpected error ensuring header row on sheet {sheet_name}: {e}")
            raise


def append_rows(sheets_service: object, rows: List[List[str]],
                spreadsheet_id: str = config.SPREADSHEET_ID,
                sheet_name: str = config.SHEET_NAME) -> Optional[Dict[str, Any]]:
    """
    Appends multiple rows of data to the Google Sheet.

    Args:
        sheets_service: The initialized Google Sheets API service object.
        rows: A list of rows to append. Each row is a list of cell values (strings).
        spreadsheet_id: The ID of the target Google Sheet document.
        sheet_name: The name of the specific sheet/tab within the document.

    Returns:
        A dictionary containing update metadata from the API response, or None if
        no rows were processed.

    Raises:
        HttpError: If the API request fails persistently (e.g., authentication error, sheet not found).
    """
    if not rows:
        logger.info("No rows to append. Skipping API call.")
        return None

    # The range specifies where to start appending. The 'append' method finds the
    # first empty row automatically.
    range_name = f"{sheet_name}!A1"
    body = {"values": rows}
    attempt = 0

    while True:
        try:
            resp: Dict[str, Any] = sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                # INSERT_ROWS is safer than OVERWRITE as it preserves data/formulas below the current sheet size.
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()

            updates = resp.get("updates", {})
            logger.info("Successfully appended %d rows to sheet %s.", len(rows), sheet_name)
            return updates

        except HttpError as e:
            attempt += 1
            # Check for rate limits or server errors for retries
            if e.resp.status in (429, 500, 503) and attempt < _MAX_ATTEMPTS:
                delay = _INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    f"HttpError appending rows (attempt {attempt}): {e.resp.status}. Retrying in {delay:.1f}s"
                )
                time.sleep(delay)
                continue
            else:
                logger.error(f"HttpError: Failed to append rows after retries on sheet {sheet_name}: {e}")
                # Re-raise the exception after exhausting retries
                raise
        except Exception as e:
            logger.error(f"Unexpected error appending rows: {e}")
            raise