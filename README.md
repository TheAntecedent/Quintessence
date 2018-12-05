The goal of Quintessence to is aggregate logs for all members in a pug group, providing a set of per-player stats and monthly/all-time bests (for DPM, heals, airshots, etc).

For an example, see the [stats for Quindali Pugs](https://docs.google.com/spreadsheets/d/13lTISEHbpGld1-wtu9dTYd3KCAoKkOegzIiRA4KhYeU/)

# Setup
1. Install all dependencies with `pipenv install`
2. Set up your google docs API credentials by following the steps on the [Google Sheets API guide](https://developers.google.com/sheets/api/quickstart/python)
    1. You only need to go through steps 1 and 2 on the guide
    2. Rename the credentials file to `google_docs_credentials.json`
3. Create a new sheet. Copy the ID from the url: `https://docs.google.com/spreadsheets/d/{THIS_IS_THE_ID_PART}/edit#gid=...`
4. In main.py, update `SPREADSHEET_ID` to the ID of that sheet

# Running the code
`pipenv run python main.py`
