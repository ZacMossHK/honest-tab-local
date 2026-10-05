from pathlib import Path
import gspread
import os

GSPREAD_SERVICE_ACCOUNT_CREDENTIALS_PATH = Path(".credentials/service_account.json")

is_test_environment = True if os.getenv("TEST") else False

gclient = gspread.service_account(GSPREAD_SERVICE_ACCOUNT_CREDENTIALS_PATH)
spreadsheet = gclient.open(
    "OBHonestyData" if not is_test_environment else "Test - OBHonestyData"
)
user_sheet = spreadsheet.worksheet("users_2026" if not is_test_environment else "users")
item_sheet = spreadsheet.worksheet("items_2026" if not is_test_environment else "items")
order_sheet = spreadsheet.worksheet(
    "orders_2026" if not is_test_environment else "orders"
)
admin_sheet = spreadsheet.worksheet(
    "admin_2026" if not is_test_environment else "admin"
)
stripe_payments_sheet = spreadsheet.worksheet("stripe_payments")
payments_sheet = spreadsheet.worksheet("payments")
checkouts_sheet = spreadsheet.worksheet("checkouts")
