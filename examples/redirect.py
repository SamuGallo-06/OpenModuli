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
# redirect.py version 1.0
#
# This script demonstrates how to redirect the user to a different page, stored in a variable.
#
# No additional dependency is required for this script as it uses Flask's built-in redirect functionality.
#

URL = "https://www.google.com"  # Example URL to redirect to

from flask import redirect, url_for

def redirect_to_page(page_name):
    """
    Redirects the user to the specified page.
    """
    return redirect(url_for(page_name))

redirect_to_page(URL)  # Example usage: redirect to the 'home' page
