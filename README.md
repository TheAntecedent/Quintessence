The goal of Quintessence to is aggregate logs for all members in a pug group, providing a set of per-player stats and monthly/all-time bests (for DPM, heals, airshots, etc).

For an example, see the [stats for Quindali Pugs](https://docs.google.com/spreadsheets/d/13lTISEHbpGld1-wtu9dTYd3KCAoKkOegzIiRA4KhYeU/)

# Setup
1. Install all dependencies
```
pipenv install google-api-python-client
pipenv install oauth2client
pipenv install gspread
pipenv install requeststhrottler
pipenv install --skip-lock requests
```
> This is a stopgap until I fix the Pipfile dependency requirement violation caused by the old version of **requeststhrottler** incorrectly pinning the required version of **requests** instead of requiring a min version

2. Set up your google docs API credentials by following step 1 on the [Google Sheets API guide](https://developers.google.com/sheets/api/quickstart/python)
    1. **You only need to go through step 1 on the guide**, but read step 4 as well to see what to expect
    2. Rename the credentials file to `google_docs_credentials.json`
3. Create a new sheet. Copy the ID from the url: `https://docs.google.com/spreadsheets/d/{THIS_IS_THE_ID_PART}/edit#gid=...`
4. In main.py, update `SPREADSHEET_ID` to the ID of that sheet

# Running the code
`pipenv run python main.py`
