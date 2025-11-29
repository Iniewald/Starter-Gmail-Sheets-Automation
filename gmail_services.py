"""

This module provides robust functions for OAuth 2.0 credential handling (obtaining,
refreshing, and saving), service initialization, and core Gmail operations,
including paginated fetching of unread emails and marking messages as read.
All network operations implement exponential backoff and retry logic for stability.

Target: Python 3.10+
"""

import os
import pickle
import time
from typing import List, Tuple, Optional, Set, Union

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Assuming these modules exist in your project structure
from utils.logger import setup_logger
import config

logger = setup_logger(__name__)

# --- Constants for API and Backoff ---
_LIST_MAX_PER_PAGE = 500  # Gmail API practical page size cap
_INITIAL_BACKOFF = 1.0  # seconds
_MAX_ATTEMPTS = 5

# Defensive defaults derived from config, ensuring a fallback value
_DEFAULT_TOKEN_PICKLE = config.TOKEN_PICKLE or "token.pickle"


# -------------------------
# Helpers
# -------------------------
def _normalize_scopes(scopes: Optional[Union[list[str], str]]) -> List[str]:
    """
    Normalize scopes coming from config or the caller into a cleaned list of strings.

    Args:
        scopes: A list of scope strings or a comma-separated string of scopes.

    Returns:
        A list of cleaned, non-empty scope strings.

    Raises:
        ValueError: If no valid scopes are provided.
    """
    if scopes is None:
        raw = config.SCOPES
    else:
        raw = scopes

    if isinstance(raw, str):
        parts = [s.strip() for s in raw.split(",")]
    elif isinstance(raw, list):
        # Convert list items to string just in case they are not
        parts = [str(s).strip() for s in raw]
    else:
        parts = []

    cleaned = [s for s in parts if s]
    if not cleaned:
        raise ValueError("No valid OAuth scopes provided. Set SCOPES in your .env/config.")
    return cleaned


def _save_credentials(token_pickle: str, creds: Credentials) -> None:
    """
    Persist credentials to disk, creating the parent directory if necessary.

    Args:
        token_pickle: Path to the file where credentials will be stored.
        creds: The authorized Credentials object to save.
    """
    parent = os.path.dirname(token_pickle) or "."
    os.makedirs(parent, exist_ok=True)
    with open(token_pickle, "wb") as f:
        pickle.dump(creds, f)
    logger.debug("Credentials saved to %s", token_pickle)


# -------------------------
# Core functions
# -------------------------
def get_credentials(
    client_secret_file: str = config.CLIENT_SECRET_FILE,
    token_pickle: str = _DEFAULT_TOKEN_PICKLE,
    scopes: Optional[List[str]] = None,
) -> Credentials:
    """
    Handles the Google OAuth 2.0 flow to obtain, refresh, and save user credentials.

    It first checks for saved credentials, refreshes them if expired, or initiates a
    new browser-based OAuth flow if no valid credentials exist or if the required
    scopes have changed.

    Args:
        client_secret_file: Path to the downloaded OAuth 2.0 client secret file.
        token_pickle: Path where the serialized credentials (token) are stored.
        scopes: A list of Google API scopes required for the application.
                Defaults to the list defined in the config module.

    Returns:
        The valid and authorized Credentials object.

    Raises:
        FileNotFoundError: If client_secret_file does not exist.
        ValueError: If scopes are missing or invalid.
        Exception: For other unexpected failures during the OAuth process.
    """
    # Validate client secret file path early
    if not os.path.exists(client_secret_file):
        raise FileNotFoundError(f"CLIENT_SECRET_FILE not found: {client_secret_file}")

    scopes_list = _normalize_scopes(scopes)

    creds: Optional[Credentials] = None

    # Try loading existing creds
    if os.path.exists(token_pickle):
        try:
            with open(token_pickle, "rb") as f:
                creds = pickle.load(f)
            logger.info("Loaded existing credentials from %s", token_pickle)
        except Exception as e:
            logger.warning("Unable to load token file %s: %s. Proceeding to re-auth.", token_pickle, e)
            creds = None

    # Check validity and determine if re-authentication/refresh is needed
    try:
        # Check if creds are missing, invalid, or if the stored scopes are insufficient
        needs_auth = (
            creds is None
            or not getattr(creds, "valid", False)
            or not set(scopes_list).issubset(set(getattr(creds, "scopes", []) or []))
        )

        if needs_auth:
            # 1. Attempt refresh if the token is expired and a refresh token exists
            if creds and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
                logger.info("Refreshing expired credentials...")
                try:
                    creds.refresh(Request())
                    logger.info("Credentials refreshed.")
                except Exception as e:
                    logger.warning("Refresh failed: %s. Falling back to full OAuth flow.", e)
                    creds = None

            # 2. Perform full OAuth flow if refresh failed or conditions weren't met
            if creds is None:
                # Clean up potentially corrupted token file
                if os.path.exists(token_pickle):
                    try:
                        os.remove(token_pickle)
                        logger.debug("Removed old/corrupted token file: %s", token_pickle)
                    except Exception:
                        logger.debug("Unable to remove token file; continuing.")

                logger.info("Starting OAuth flow in local browser...")
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes_list)
                # Opens a local browser for user authentication
                creds = flow.run_local_server(port=0)
                logger.info("OAuth flow completed successfully.")
    except Exception as e:
        logger.error("Failed obtaining credentials: %s", e)
        raise

    # Persist the final, valid credentials before returning
    try:
        _save_credentials(token_pickle, creds)
    except Exception as e:
        logger.warning("Failed to save credentials to %s: %s", token_pickle, e)

    return creds


def build_services(creds: Credentials) -> Tuple[object, object]:
    """
    Initializes and builds the Google Gmail and Sheets API service objects.

    Args:
        creds: The authorized Credentials object.

    Returns:
        A tuple containing the initialized Gmail service object and Sheets service object.

    Raises:
        Exception: If the service objects cannot be initialized (e.g., wrong API name/version).
    """
    try:
        # Build Gmail API service (version v1)
        gmail_service = build("gmail", "v1", credentials=creds)
        # Build Google Sheets API service (version v4)
        sheets_service = build("sheets", "v4", credentials=creds)

        logger.info("Google API services built (Gmail + Sheets).")
        return gmail_service, sheets_service
    except Exception as e:
        logger.error("Failed to build Google API services: %s", e)
        raise


def fetch_unread_full_emails(gmail_service: object,
                             max_results: int = config.MAX_RESULTS,
                             query: str = config.GMAIL_SEARCH_QUERY) -> List[dict]:
    """
    Fetches the full payload of up to `max_results` unread emails, handling API pagination.

    The process involves:
    1. Paginatedly listing message IDs using a custom query.
    2. Deduplicating the collected IDs.
    3. Iterating through the unique IDs to fetch the full message payload (format='full').
    Both listing and fetching steps include retries with exponential backoff for resilience.

    Args:
        gmail_service: Initialized Gmail API service object.
        max_results: Maximum total number of full messages to retrieve.
                     Defaults to config.MAX_RESULTS.

    Returns:
        A list of dictionaries, where each dictionary is the full message payload.
        Returns an empty list if `max_results` is non-positive or on irrecoverable error.
    """
    if max_results <= 0:
        logger.info("max_results <= 0; returning empty list.")
        return []

    logger.info("Starting unread email fetch (max_results=%s)...", max_results)

    all_ids: List[dict] = []
    page_token: Optional[str] = None

    # 1) Listing loop with pagination & retries (for batch failures)
    while len(all_ids) < max_results:
        # Calculate size for the current API call (cap at max_results or _LIST_MAX_PER_PAGE)
        batch_size = min(max_results - len(all_ids), _LIST_MAX_PER_PAGE)
        attempt = 0

        while True:
            try:
                # Execute the list request
                resp = gmail_service.users().messages().list(
                    userId="me",
                    q=query,
                    maxResults=batch_size,
                    pageToken=page_token,
                ).execute()
                break  # Success, exit retry loop
            except HttpError as he:
                attempt += 1
                delay = _INITIAL_BACKOFF * (2 ** attempt)
                logger.warning("HttpError listing messages (attempt %d): %s. Retrying in %.1fs", attempt, he, delay)
                if attempt >= _MAX_ATTEMPTS:
                    logger.error("Too many retries listing messages; aborting list phase.")
                    return []  # Abort early, safer for client
                time.sleep(delay)
            except Exception as e:
                logger.error("Unexpected error listing messages: %s", e)
                return []

        messages = resp.get("messages", [])
        if messages:
            all_ids.extend(messages)
            logger.info("Collected %d message IDs (total %d).", len(messages), len(all_ids))
        else:
            logger.debug("No messages returned in this page.")

        page_token = resp.get("nextPageToken")
        # Stop if no next page token or we've reached desired count
        if not page_token or len(all_ids) >= max_results:
            break

    # Deduplicate IDs (important if messages are retrieved across multiple list calls)
    seen: Set[str] = set()
    unique_ids: List[dict] = []
    for m in all_ids:
        mid = m.get("id")
        if mid and mid not in seen:
            seen.add(mid)
            unique_ids.append(m)
    # Trim the list to max_results in case the last page exceeded the soft cap
    unique_ids = unique_ids[:max_results]
    logger.info("Finished list phase. Attempting to fetch %d unique messages.", len(unique_ids))

    # 2) Fetch full messages with retry/backoff per message
    full_messages: List[dict] = []
    for idx, mid_dict in enumerate(unique_ids):
        msg_id = mid_dict.get("id")
        if not msg_id:
            continue

        attempt = 0
        while True:
            try:
                full = gmail_service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="full",
                ).execute()
                full_messages.append(full)
                logger.debug("Fetched full message %s (%d/%d)", msg_id, idx + 1, len(unique_ids))
                break  # Success, exit retry loop
            except HttpError as he:
                attempt += 1
                delay = _INITIAL_BACKOFF * (2 ** attempt)
                logger.warning("HttpError fetching message %s (attempt %d): %s. Retrying in %.1fs", msg_id, attempt, he, delay)
                if attempt >= _MAX_ATTEMPTS:
                    logger.error("Failed to fetch message %s after %d attempts; skipping.", msg_id, attempt)
                    break # Skip to next message
                time.sleep(delay)
            except Exception as e:
                logger.error("Unexpected error fetching message %s: %s", msg_id, e)
                break # Skip to next message

    logger.info("Completed fetch: %d full messages retrieved.", len(full_messages))
    return full_messages


def mark_as_read(gmail_service: object, msg_id: str, max_attempts: int = _MAX_ATTEMPTS) -> None:
    """
    Remove the 'UNREAD' label from the message, marking it as read.

    Implements retries with exponential backoff on network/API errors.

    Args:
        gmail_service: Initialized Gmail API service object.
        msg_id: The ID of the message to be marked as read.
        max_attempts: The maximum number of times to attempt the operation.
    """
    attempt = 0
    while True:
        try:
            # The modify API call removes the 'UNREAD' label
            gmail_service.users().messages().modify(
                userId="me",
                id=msg_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            logger.debug("Marked message %s as read.", msg_id)
            return  # Success, exit function
        except HttpError as he:
            attempt += 1
            delay = _INITIAL_BACKOFF * (2 ** attempt)
            logger.warning("HttpError marking read for %s (attempt %d): %s. Retrying in %.1fs", msg_id, attempt, he, delay)
            if attempt >= max_attempts:
                logger.error("Failed to mark %s as read after %d attempts; giving up.", msg_id, attempt)
                return
            time.sleep(delay)
        except Exception as e:
            logger.error("Unexpected error marking %s as read: %s", msg_id, e)
            return