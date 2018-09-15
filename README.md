# Setup
1. Install all dependencies with `pipenv install`
2. Set up your google docs API credentials by following the steps on the [Google Sheets API guide](https://developers.google.com/sheets/api/quickstart/python)
    1. You only need to go through steps 1 and 2 on the guide
    2. Rename the credentials file to `google_docs_credentials.json`
3. Create a new sheet. Copy the ID from the url: `https://docs.google.com/spreadsheets/d/{THIS_IS_THE_ID_PART}/edit#gid=...`
4. In main.py, update `SPREADSHEET_ID` to the ID of that sheet

# Running the code
`pipenv run python main.py`
