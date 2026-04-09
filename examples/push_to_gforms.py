# OpenModuli - Open Source, Self-Hosted Form Builder and Management System.
# Copyright (C) 2025 Samuele Gallicani
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# OpenModuli Example Scripts
# push_to_gforms.py version 2.1
#
# This script appends form data to a Google Sheets worksheet.
# It reads the payload from stdin, creates missing headers if needed,
# and appends one new row per execution.
#
# Configuration constants:
# - Set SPREADSHEET_ID to your Google Sheet ID
# - Set WORKSHEET_NAME to the target tab name
# - Set CREDENTIALS_FILE to the service account JSON path
# Dependencies:
# - gspread
# - google-auth
#
# Make sure to install the required dependencies using 
#   `pip install gspread google-auth` 
# and set up a Google Cloud service account with the appropriate permissions.
# Share the target spreadsheet with the service account email
# to allow access.


from __future__ import annotations

import json
import sys

import gspread

SPREADSHEET_ID = ""
WORKSHEET_NAME = "Sheet1"
CREDENTIALS_FILE = "service_account.json"
DEFAULT_WORKSHEET_NAME = "Sheet1"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def read_form_payload() -> dict:
    """Read the payload passed by OpenModuli on stdin."""
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def _normalize_cell_value(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _get_client(credentials_file: str | None = None) -> gspread.Client:
    if credentials_file:
        return gspread.service_account(filename=credentials_file, scopes=SCOPES)
    return gspread.service_account(scopes=SCOPES)


def _ensure_headers(worksheet, field_names):
    existing_headers = worksheet.row_values(1)

    if not existing_headers:
        headers = list(field_names)
        if headers:
            worksheet.update("A1", [headers], value_input_option="RAW")
        return headers

    headers = list(existing_headers)
    for field_name in field_names:
        if field_name not in headers:
            headers.append(field_name)

    if headers != existing_headers:
        worksheet.update("A1", [headers], value_input_option="RAW")

    return headers


def push_to_google_sheets(spreadsheet_id, worksheet_name, form_data, credentials_file=None):
    """
    Append a new row to a Google Sheet using the form fields as columns.

    :param spreadsheet_id: The Google Sheets spreadsheet ID.
    :param worksheet_name: The target worksheet/tab name.
    :param form_data: A dictionary containing the form data to be sent.
    :param credentials_file: Optional path to the service account JSON file.
    """
    client = _get_client(credentials_file)
    worksheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)

    field_names = list(form_data.keys())
    headers = _ensure_headers(worksheet, field_names)
    row = [_normalize_cell_value(form_data.get(field_name, "")) for field_name in headers]
    worksheet.append_row(row, value_input_option="USER_ENTERED")  # type: ignore[arg-type]


if __name__ == "__main__":
    payload = read_form_payload()
    form_name = payload.get("form_name", "")
    values = payload.get("values", {})

    spreadsheet_id = SPREADSHEET_ID.strip()
    worksheet_name = (WORKSHEET_NAME.strip() or DEFAULT_WORKSHEET_NAME)
    credentials_file = CREDENTIALS_FILE.strip() or None

    if not spreadsheet_id:
        raise SystemExit("Missing SPREADSHEET_ID constant.")

    push_to_google_sheets(spreadsheet_id, worksheet_name, values, credentials_file=credentials_file)
    print(f"Data successfully appended to Google Sheets for form '{form_name}'.")

