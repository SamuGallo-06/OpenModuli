# OpenModuli
Self-hosted, open-source tool for creating and managing online forms and generating PDFs from them. 
Built with Flask and Python, it offers a user-friendly interface for form design, data collection, and PDF generation. 
Ideal for organizations needing customizable form solutions without relying on third-party services.

## Features
- PDF Export: Unlike Google Forms, OpenModuli allows you to export form responses as compact PDF documents, making it easier to share and archive data, or print them.
- Customizable Forms: Create and manage your own forms with a user-friendly builder, without needing to write code.
- Self-Hosted: You have full control over your data and the application, as it runs on your own server or local machine.
- Customizable Branding: Personalize the look and feel of your forms and PDFs with your organization's branding, including colors, logos, and contact information.

## Add an Admin User
OpenModuli supports admin user creation via Flask CLI.

1. Activate your virtual environment.
2. Initialize the database tables (if needed):

```bash
flask --app main init-db
```

3. Create an admin user:

```bash
flask --app main create-admin <username>
```

The command prompts for the password securely.

Notes:
- If the username already exists, the command returns an error.
- On first startup, the initial setup wizard can also create or update the admin user.
