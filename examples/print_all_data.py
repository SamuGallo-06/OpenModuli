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
