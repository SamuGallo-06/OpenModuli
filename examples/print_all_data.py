#OpenModuli Example Scripts
# print_all_data.py version 1.0
#
# This script demonstrates how to print all submitted form data in the console.
# It retrieves the current form data and prints it in a readable format.
# Form data is given as input
#

"""
standard definition for retrieving form data.
"""
import sys
import json

raw = sys.stdin.read() # read raw JSON data from stdin
data = json.loads(raw) if raw.strip() else {}

form_name = data.get("form_name")
values = data.get("values", {})

"""end of standard definition"""

print("Form:", form_name)
print("Values:", values)
