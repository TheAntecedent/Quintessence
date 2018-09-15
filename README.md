# Setup
1. Install all dependencies with `pipenv install`
2. Set up your google docs API credentials by following the steps on the [Google Sheets API guide](https://developers.google.com/sheets/api/quickstart/python)
  a. You only need to go through steps 1 and 2 on the guide
  b. Rename the credentials file `google_docs_credentials.json`

# Running the code
0. In main.py, update `SPREADSHEET_ID` to the ID of a spreadsheet that you've created that you want the script to modify
1. Run `pipenv run python main.py`
