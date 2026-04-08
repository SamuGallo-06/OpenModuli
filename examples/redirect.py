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
