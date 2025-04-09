
import os
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

# The ID and range of the spreadsheets.
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
MAIN_RANGE_NAME = "Active!A2:M"
NXDOMAIN_RANGE_NAME = "Down!A2:M"

def extract_domain(url):
    pattern = r'^(?:https?://)?(.*?)/?$'
    match = re.match(pattern, url)
    return match.group(1) if match else None

def assert_and_append_domain_slash(domain):
    # Normalize the domain by ensuring it starts with "https://"
    # and ends with a trailing slash.
    if not domain.endswith("/"):
        domain = domain + "/"
    if not domain.startswith("https://"):
        domain = "https://" + domain
    return domain

def get_dns_status_and_ip(domain, nameserver='8.8.8.8'):
    """
    Perform DNS lookups using dns.resolver.Resolver.
    Returns ("NOERROR", <first_ip>) if an A or AAAA record is found,
    or (None, None) otherwise.
    """
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [nameserver]
    resolver.timeout = 3
    resolver.lifetime = 3

    try:
        # Try to resolve an A record.
        answer = resolver.resolve(domain, 'A')
        if answer:
            first_ip = answer[0].to_text()
            print(f"Domain: {domain} - Status: NOERROR - Found A record: {first_ip}")
            return "NOERROR", first_ip
    except dns.resolver.NoAnswer:
        print(f"No A record found for {domain}.")
    except dns.exception.Timeout:
        print(f"DNS query timed out for {domain}.")
        return None, None
    except Exception as e:
        print(f"Unexpected DNS error for {domain} (A record): {e}")

    try:
        # If no A record, try for an AAAA record.
        answer = resolver.resolve(domain, 'AAAA')
        if answer:
            first_ip = answer[0].to_text()
            print(f"Domain: {domain} - Status: NOERROR - Found AAAA record: {first_ip}")
            return "NOERROR", first_ip
    except dns.resolver.NoAnswer:
        print(f"No AAAA record found for {domain}.")
    except dns.exception.Timeout:
        print(f"DNS query timed out for {domain}.")
        return None, None
    except Exception as e:
        print(f"Unexpected DNS error for {domain} (AAAA record): {e}")

    return None, None

def main():
    """Reads domains from the Active sheet, checks the URL,
    and appends the row to either the valid or down list."""
    creds = None
    token_path = r"C:\Users\smabry\Desktop\REPOS\domain_filtration_automation\token.json"
    creds_file = r"C:\Users\smabry\Desktop\REPOS\domain_filtration_automation\credentials.json"
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()

        # Retrieve data from the Active sheet.
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=MAIN_RANGE_NAME).execute()
        values = result.get("values", [])
        
        # Retrieve previously filtered (down) rows.
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=NXDOMAIN_RANGE_NAME).execute()
        previous_dead_links = result.get("values", [])
        down_rows = previous_dead_links.copy()

        if not values:
            print("No data found.")
            return
        

        valid_rows = []
        for row in values:
            if not row:
                continue
            # Assume the URL is in column 2 (index 1).
            domain = extract_domain(row[1].strip())
            status, first_ip = get_dns_status_and_ip(domain)
            # Normalize the domain.
            row[1] = assert_and_append_domain_slash(domain)
            if status == "NOERROR" and first_ip:
                try:
                    row[2] = first_ip  # Store the resolved IP in column 3.
                except:
                    pass
                finally:
                    valid_rows.append(row)
            else:
                down_rows.append(row)

        # Clear and update the Active sheet with valid domains.
        sheet.values().clear(spreadsheetId=SPREADSHEET_ID, range=MAIN_RANGE_NAME).execute()
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=MAIN_RANGE_NAME,
            valueInputOption="RAW",
            body={"values": valid_rows},
        ).execute()

        # Clear and update the Down sheet with domains that did not resolve.
        sheet.values().clear(spreadsheetId=SPREADSHEET_ID, range=NXDOMAIN_RANGE_NAME).execute()
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=NXDOMAIN_RANGE_NAME,
            valueInputOption="RAW",
            body={"values": down_rows},
        ).execute()

    except HttpError as err:
        print(err)

if __name__ == "__main__":
    main()

