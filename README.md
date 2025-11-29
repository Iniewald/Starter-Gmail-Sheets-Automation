SECURE GMAIL TO GOOGLE SHEETS AUTOMATION PIPELINE



PROJECT OVERVIEW

This is a robust, production-ready Python script designed to automatically and securely extract specific data from your incoming Gmail messages and write it directly to a Google Sheet.

This solution eliminates manual data entry, saving you time and ensuring 100% data accuracy.



KEY FEATURES

\- Secure Authentication: Uses Google OAuth 2.0 for secure access (no passwords required). Tokens are refreshed automatically.

\- Enterprise Stability: Implements Exponential Backoff and Retries on all API calls, ensuring the script handles network errors and Google rate limits without crashing.

\- Flexible Data Parsing: Uses a data-driven configuration map (config.py) that allows you to easily change or add new data fields without modifying the core logic.

\- Clean Operation: Only processes unread emails matching a specific search query, then marks them as read.



SETUP GUIDE (5 Steps to Automation)

---

Prerequisites

Ensure you have Python 3.10+ installed on your system.



Install Dependencies

To ensure the project runs without conflicting with other software on your system, you must use a virtual environment.

1. Create Environment:
Open your terminal or command prompt, navigate to the project directory, and create the environment (we recommend naming it 'venv'):
python -m venv venv

2. Activate Environment:
You MUST activate the environment every time you open a new terminal session before running the script.

    - Windows (Command Prompt):
      venv\Scripts\activate.bat

    - Windows (PowerShell):
      venv\Scripts\Activate.ps1

    - macOS / Linux:
      source venv/bin/activate

3. Install Requirements:
With the environment activated, install all necessary libraries:
pip install -r requirements.txt

(You should see '(venv)' or similar text at the start of your terminal prompt when the environment is active.)


Secure Google API Setup (Critical Step)

This process securely links your script to your Google account.

A. Enable APIs: Go to the Google Cloud Console. Ensure the \*\*Gmail API\*\* and \*\*Google Sheets API\*\* are Enabled for your project.

B. Download Credentials: Navigate to APIs \& Services > Credentials. Create an OAuth client ID for a \*\*Desktop app\*\*.

C. Click the \*\*Download JSON\*\* button and rename the file to \*\*client\_secret.json\*\*.

D. Place the \*\*client\_secret.json\*\* file directly into the root directory of this project.



Configuration (The .env File)

You must create a new file named \*\*.env\*\* (note the starting dot) in the root of the project directory. Use the provided .env.example as a guide.



| Variable | Description |

| SPREADSHEET\_ID | The unique ID from your Google Sheet URL (e.g., 1BsyG...Q4o3).

| SHEET\_NAME | The exact name of the tab in your spreadsheet (e.g., Sheet1 or Processed Data).

| CLIENT\_SECRET\_FILE | Do not change. Must be set to client\_secret.json.

| MAX\_RESULTS | The maximum number of unread emails to process per run (e.g., 50).

| HIGH\_PRIORITY\_KEYWORDS | The keywords you want your program to check for when determining priority.

| LOG\_LEVEL | Set to INFO. This controls how much detail is saved to the log file.

| GMAIL\_SEARCH\_QUERY | CRITICAL: The string used to filter which unread emails are fetched.



Define Your Data Fields (config.py)

This file is already configured by your developer (me!) for your specific emails, but it's important to understand how it works.

The \*\*PARSING\_MAP\*\* is a list of dictionaries that tell the script exactly where to look in the email (Header, Body, or Subject) and what pattern (Key/Value, RegEx) to use to extract your data fields.



Detailed Search Query Setup

The \*\*GMAIL\_SEARCH\_QUERY\*\* variable determines exactly which emails the script will process. It uses the same advanced search operators you would use in the Gmail search bar.



\- Rule 1: Always include \*\*`is:unread`\*\*. This ensures the script only processes new emails.

\- Rule 2: Combine operators with spaces. (e.g., `is:unread from:amazon subject:shipment`)



| Operator | Purpose | Example |

| from: | Filters emails from a specific sender. | from:orders@acme.com |

| subject: | Filters emails containing a specific word or phrase in the subject line. | subject:"New Order Confirmation" |

| has:attachment | Filters emails that contain any file attachment. | has:attachment |



Example Search String (for .env):

GMAIL\_SEARCH\_QUERY=is:unread from:tracking@shipping.co subject:"Your package has shipped"



First Run and Authentication

Ensure all previous steps are complete.

Run the main pipeline from your Terminal:

python pipeline.py



Authentication: The first time you run it, a browser window will open. Sign in and grant permissions.

Secure Token: Once authenticated, a file named \*\*token.pickle\*\* will appear in your project folder. This is your secure login key. Do not delete this file.



Subsequent Runs

To run the automation again at any time, simply repeat the command from Step 6. The script will use the saved token and run automatically.

---

TROUBLESHOOTING AND SUPPORT

If the script fails, please check the following:

\- Check Logs: Review the files in the \*\*logs/\*\* directory for specific error messages.

\- Verify Configuration: Double-check the \*\*SPREADSHEET\_ID\*\* and \*\*SHEET\_NAME\*\* in your \*\*.env\*\* file for typos.

\- Need Assistance? Your service tier includes 7 days of free support to guarantee a successful launch. Please contact me directly if you encounter any issues.

"# Starter-Gmail-Sheets-Automation" 
