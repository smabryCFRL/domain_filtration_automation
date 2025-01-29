import os.path
import re

import dns.resolver
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


load_dotenv()


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
MAIN_SHEET_ID =  os.getenv("MAIN_SHEET_ID")
DELETED_SHEET_ID = os.getenv("DELETED_SHEET_ID")
MAIN_RANGE_NAME = "Active!A2:L"
NXDOMAIN_RANGE_NAME = "Down!A2:L"
def extract_domain(url):
    if not url:
        return
    pattern = r"^(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:/.*)?$"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_dns_status(domain, rdtype='A', nameserver='8.8.8.8'):
    query = dns.message.make_query(domain, rdtype)
    try:
        print(f"Querying DNS status for {domain}")
        response = dns.query.udp(query, nameserver, timeout=2)
        status_code = response.rcode()
        print(f"Domain{domain} - Status:{dns.rcode.to_text(status_code)}")
        return dns.rcode.to_text(status_code)
    except dns.exception.Timeout:
        print(f"DNS query timed out for {domain}")
        return None
    except Exception as e:
        print(f"DNS query unexpected error for {domain}: {e}")
        return None

def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=MAIN_RANGE_NAME)
            .execute()
        )
        values = result.get("values", [])

        if not values:
            print("No data found.")
            return

        valid_rows = []
        filtered_rows = []
        for row in values:
            if not row:
                continue
            domain = extract_domain(row[1].strip())
            if not domain:
                continue
            status = get_dns_status(domain)
            if status == "NOERROR":
                valid_rows.append(row)
            else:
                filtered_rows.append(row)
                
                
        result = sheet.values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=MAIN_RANGE_NAME,
        ).execute()

        result = sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=MAIN_RANGE_NAME,
            valueInputOption = "RAW",
            body = {"values": valid_rows}
        ).execute()

        
        result = sheet.values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=NXDOMAIN_RANGE_NAME,
        ).execute()

        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=NXDOMAIN_RANGE_NAME,
            valueInputOption = "RAW",
            body = {"values": filtered_rows}
        ).execute()
             
    except HttpError as err: 
        print(err)
        filename = "failure.txt"
        with open(filename, 'w') as file:
            file.write(err)
            file.close()
    filename2 = "Success.txt"
    with open(filename2, 'w') as file:
        file.write("Success!")
        file.close()

if __name__ == "__main__":
  main()