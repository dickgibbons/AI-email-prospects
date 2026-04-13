# EPAM Outreach Agent System — Setup

This system runs as a Python script on your Ubuntu VPS via cron. Five agents (Selector, Researcher, Writer, Publisher, Reminder) are orchestrated by `run_daily.py`.

---

## 1. Prerequisites

- Ubuntu VPS with internet access
- Python 3.10+ (check with `python3 --version`)
- A Google Cloud project with the Sheets API, Drive API, and Docs API enabled
- A Google service account (JSON key file) with access to your Sheet and Drive folders
- An Anthropic API key
- A Gmail App Password for dickgibbons@gmail.com

### Install Python 3.11 (if needed)

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y
```

---

## 2. Clone and set up

```bash
cd /opt  # or wherever you want the project
git clone <your-repo-url> "AI Email Prospects"
cd "AI Email Prospects"

python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Google service account

1. Go to [Google Cloud Console](https://console.cloud.google.com/) > your project > **IAM & Admin** > **Service Accounts**.
2. Create a service account (e.g. `epam-outreach@your-project.iam.gserviceaccount.com`).
3. Download the JSON key file.
4. Place it at `config/service_account.json` (or set `GOOGLE_SERVICE_ACCOUNT_FILE` env var to a different path).
5. Enable these APIs in the project: **Google Sheets API**, **Google Drive API**, **Google Docs API**.
6. Share your Google Sheet with the service account email (Editor access).
7. Share the **EPAM** root folder in Drive with the service account email (Editor access). This gives it access to the entire folder tree.

---

## 4. Google Sheet

- Sheet name: **Contacts** (or set `SHEET_NAME` env var).
- Columns (row 1 headers, exact spelling):

  `Name | Title | Company | LinkedIn URL | Target vs Existing | Intro Call Topic | EPAM Footprint | Internal Contact | Notes | Status | Max Touches | Last Touch Sent | Next Touch Due | Doc Link | Last Processed`

- See `docs/SHEET_SCHEMA.md` for full column definitions and selection rules.
- Copy the **Spreadsheet ID** from the sheet URL: `https://docs.google.com/spreadsheets/d/<THIS_PART>/edit`.

---

## 5. Drive folder structure

Create this structure in Google Drive (the Publisher agent will auto-create company and sender folders, but the top-level structure must exist):

```
EPAM/
  EPAM Client Outreach/
    Client/
      Messages/
    Target Prospect/
      Messages/
```

Copy the **EPAM** folder ID from Drive (right-click > Get link > extract the ID from the URL, or use `drive.google.com/drive/folders/<THIS_PART>`).

---

## 6. Gmail App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (logged in as dickgibbons@gmail.com).
2. Generate an App Password for "Mail" > "Other (Custom name)" > name it "EPAM Outreach".
3. Copy the 16-character password.

---

## 7. Environment variables

Set these in your shell, `.env` file, or crontab. All are required unless noted.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export SPREADSHEET_ID="1abc..."
export DRIVE_ROOT_FOLDER_ID="1xyz..."
export GMAIL_APP_PASSWORD="abcd efgh ijkl mnop"

# Optional overrides (defaults shown):
# export CLAUDE_MODEL="claude-sonnet-4-20250514"
# export GOOGLE_SERVICE_ACCOUNT_FILE="/opt/AI Email Prospects/config/service_account.json"
# export SHEET_NAME="Contacts"
# export GMAIL_ADDRESS="dickgibbons@gmail.com"
# export REMINDER_TO="richard_gibbons@epam.com"
```

---

## 8. Test run

```bash
cd "/opt/AI Email Prospects"
source venv/bin/activate

# Dry run — prints what would happen, no API calls or writes:
python run_daily.py --dry-run

# Full run — processes prospects, creates Docs, updates Sheet, sends reminder:
python run_daily.py
```

Check `logs/` and console output for results.

---

## 9. Cron (daily at 7:00 AM EST)

```bash
crontab -e
```

Add:

```
0 7 * * * cd "/opt/AI Email Prospects" && /opt/AI\ Email\ Prospects/venv/bin/python run_daily.py >> logs/daily.log 2>&1
```

Make sure the environment variables are available to cron. Options:
- Source an env file in the cron command: `source /opt/AI\ Email\ Prospects/.env && python run_daily.py`
- Or set them directly in the crontab file above the cron entry.

---

## 10. Stopping a sequence

To stop outreach to a prospect:
- Set their **Status** to `Stopped`, `Not interested`, `Meeting booked`, or `Done` in the Sheet.
- The Selector agent only processes rows with Status = `New` or `In sequence`.
- You can also delete the row entirely.

---

## 11. Adding new prospects

1. Add a row to the Contacts sheet with at least: **Name**, **Company**, **LinkedIn URL**.
2. Set **Status** = `New`.
3. Fill in as much as possible: Title, Target vs Existing, Intro Call Topic, EPAM Footprint, Internal Contact, Notes.
4. Leave Last Touch Sent, Next Touch Due, Doc Link, Last Processed blank.
5. The next daily run will pick them up (subject to max 20 per run, 3 per company).

---

## 12. Company background docs (optional)

For richer research, create a Google Doc named with "background" in the title (e.g. "Company background — BBH") in the company's folder:

```
EPAM / EPAM Client Outreach / Target Prospect / Messages / Brown Brothers Harriman / Company background — BBH
```

The Researcher agent will find and read it automatically.
