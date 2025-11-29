from typing import List, Any, Dict, Optional
from googleapiclient.errors import HttpError
from utils.logger import setup_logger
import config
import time

logger = setup_logger(__name__)

_INITIAL_BACKOFF = 1.0  # seconds
_MAX_ATTEMPTS = 5

def ensure_header_row(sheets_service: object, header: List[str],
                      spreadsheet_id: str = config.SPREADSHEET_ID,
                      sheet_name: str = config.SHEET_NAME) -> None:
    """
    Checks if the first row of the Google Sheet contains a header. If the row is
    empty or contains only whitespace, a predefined header row is written.

    This provides a consistent starting point for the data export.

    Args:
        sheets_service: The initialized Google Sheets API service object.
        spreadsheet_id: The ID of the target Google Sheet document.
        sheet_name: The name of the specific sheet/tab within the document.

    Raises:
        HttpError: If the API request fails (e.g., authentication error, sheet not found).
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

            # Check if the first row exists and has any non-whitespace content
            is_header_present = values and any(cell.strip() for cell in values[0])

            if is_header_present:
                logger.debug("Header already exists in sheet %s.", sheet_name)
                return

            # 2. Write the header if it's missing
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
            if e.resp.status in (429, 500, 503) and attempt < _MAX_ATTEMPTS:
                delay = _INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    f"HttpError writing header (attempt {attempt}): {e.resp.status}. Retrying in {delay:.1f}s"
                )
                time.sleep(delay)
                continue
            else:
                logger.error(f"HttpError: Failed to ensure header row after retries on sheet {sheet_name}: {e}")
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
        HttpError: If the API request fails (e.g., authentication error, sheet not found).
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
                # INSERT_ROWS pushes existing content down and inserts new rows
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()

            updates = resp.get("updates", {})
            logger.info("Successfully appended %d rows to sheet %s.", len(rows), sheet_name)
            return updates

        except HttpError as e:
            attempt += 1
            if e.resp.status in (429, 500, 503) and attempt < _MAX_ATTEMPTS:
                delay = _INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    f"HttpError appending rows (attempt {attempt}): {e.resp.status}. Retrying in {delay:.1f}s"
                )
                time.sleep(delay)
                continue
            else:
                logger.error(f"HttpError: Failed to append rows after retries on sheet {sheet_name}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error appending rows: {e}")
            raise