SECURE GMAIL TO GOOGLE SHEETS AUTOMATION PIPELINE

PROJECT OVERVIEW

This is a robust, production-ready Python script designed to automatically and securely extract specific, structured data from your incoming Gmail messages and write it directly to a Google Sheet.

This solution eliminates manual data entry, saving you significant time and ensuring 100% data accuracy by running a reliable, fault-tolerant workflow.

KEY FEATURES

Secure Authentication: Uses Google OAuth 2.0 for secure, token-based access. No passwords are stored, and tokens are refreshed automatically.

Enterprise Stability: Implements Exponential Backoff and Retries on all API calls (Gmail and Sheets), ensuring the script gracefully handles network errors and Google rate limits without crashing.

Data Integrity: Emails are only marked as read AFTER successful confirmation that the data has been safely exported to the Google Sheet.

Flexible Data Parsing (Scope): Uses a data-driven configuration map (config.py) designed for robust, all-rounded data extraction. This map is tailored for standard email formats (key/value pairs, structured codes).

Scope Limitation: The script is optimized for Key: Value and simple formats. It does NOT support fields that are adjacent on the same line or deeply nested in tables, which require custom RegEx development (available in the Premium/Custom tier).

Clean Operation: Only processes unread emails matching a specific search query.

SETUP GUIDE (5 Steps to Automation)

Step 1: Install Dependencies

To ensure the project runs without conflicting with other Python software on your system, you must use a virtual environment.

Create Environment:
Open your terminal or command prompt, navigate to the project directory, and create the environment (we recommend naming it 'venv'):

python -m venv venv

Activate Environment:
You MUST activate the environment every time you open a new terminal session before running the script.

OS

Command

Windows (Command Prompt)

venv\Scripts\activate.bat

Windows (PowerShell)

venv\Scripts\Activate.ps1

macOS / Linux

source venv/bin/activate

Install Requirements:
With the environment activated (you should see (venv) at your prompt), install all necessary libraries:

pip install -r requirements.txt

Step 2: Secure Google API Setup (CRITICAL)

This process securely links your script to your Google account and is required only once.

A. Enable APIs: Go to the Google Cloud Console. Ensure the Gmail API and Google Sheets API are Enabled for your project.

B. Download Credentials: Navigate to APIs & Services > Credentials.

Click Create Credentials and choose OAuth client ID.

For the Application Type, select Desktop app.

Click the Download JSON button and rename the file to client_secret.json.

Place the client_secret.json file directly into the root directory of this project.

Step 3: Configuration (.env File)

You must create a new file named .env (note the starting dot) in the root of the project directory. Use the provided .env.example as a guide.

Variable

Description

SPREADSHEET_ID

The unique ID from your Google Sheet URL (e.g., 1BsyG...Q4o3).

SHEET_NAME

The exact name of the tab in your spreadsheet (e.g., Sheet1 or Processed Data).

CLIENT_SECRET_FILE

Do not change. Must be set to client_secret.json.

MAX_RESULTS

The maximum number of unread emails to process per run (e.g., 50).

HIGH_PRIORITY_KEYWORDS

Comma-separated list of keywords to check for (e.g., URGENT, ACTION NEEDED, High Priority).

LOG_LEVEL

Set to INFO. Controls how much detail is saved to the log file.

GMAIL_SEARCH_QUERY

CRITICAL: The string used to filter which unread emails are fetched.

Step 4: Define Your Data Fields (config.py)

This file contains the PARSING_MAP, which is the core logic for data extraction. The developer (me!) configured this for your specific email format.

The PARSING_MAP is a list of instructions that tell the script exactly where to look (Header, Body) and what pattern (Key/Value, RegEx) to use to extract your custom data fields. Changing the fields here will automatically update the column headers in your Google Sheet.

Step 5: Run the Pipeline

Ensure your virtual environment is active (Step 1).

First Run and Authentication:
Run the main pipeline from your Terminal:

python pipeline.py

The first time, a browser window will open. Sign in and grant permissions. Once authenticated, a file named token.pickle will appear in your project folder. This is your secure login key; do not delete this file.

Subsequent Runs:
To run the automation again at any time, simply ensure the environment is active and repeat the command. The script will use the saved token and run automatically.

Detailed Search Query Setup

The GMAIL_SEARCH_QUERY variable uses the same advanced search operators you would use in the Gmail search bar.

Rule 1: Always include is:unread. This ensures the script only processes new emails and avoids reprocessing old ones.

Rule 2: Combine operators with spaces. (e.g., is:unread from:amazon subject:shipment)

Operator

Purpose

Example

is:unread

Mandatory filter for new emails.

is:unread

from:

Filters emails from a specific sender.

from:orders@acme.com

subject:

Filters emails containing a specific phrase in the subject line.

subject:"New Order Confirmation"

has:attachment

Filters emails that contain any file attachment.

has:attachment

Example Search String (for .env):
GMAIL_SEARCH_QUERY=is:unread from:tracking@shipping.co subject:"Your package has shipped"

TROUBLESHOOTING AND SUPPORT

If the script fails or produces unexpected results, please check the following:

Check Logs: Review the files in the logs/ directory for specific error messages and stack traces.

Verify Configuration: Double-check the SPREADSHEET_ID and SHEET_NAME in your .env file for typos.

Mismatched Header: If you see a ValueError: Mismatched Google Sheet header detected, you must clear the first row of your Google Sheet to allow the script to write the required column names.

Need Assistance? Your service tier includes 7 days of free support to guarantee a successful launch. Please contact me directly if you encounter any issues.