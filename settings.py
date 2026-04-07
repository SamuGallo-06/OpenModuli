import os
import xml.etree.ElementTree as ET

import bcrypt

settings = {}

DEFAULT_SETTINGS = {
    "general": {
        "language": "it",
        "first_access": "true",
    },
    "paths": {
        "forms_path": "forms",
        "pdf_path": "pdfs",
    },
    "entity": {
        "logo_image": "",
        "entity_name": "OpenModuli",
        "entity_address": "",
        "entity_contacts": "",
        "entity_phone": "",
    },
    "personalization": {
        "primary_color": "",
        "secondary_color": "",
        "background_image": "",
    },
    "access": {
        "current_password": "",
        "new_password": "",
        "confirm_password": "",
    },
}


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for the provided plaintext password."""
    password = (plain_password or "").encode("utf-8")
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify plaintext password against a bcrypt hash.

    For backward compatibility, plaintext values are accepted and compared directly.
    """
    plain = (plain_password or "")
    stored = (stored_hash or "")
    if not stored:
        return False

    if stored.startswith("$2"):
        return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))

    return plain == stored


def _ensure_password_hashed() -> bool:
    """Ensure settings['access']['current_password'] is stored as bcrypt hash.

    @return True if a migration/update happened, False otherwise.
    """
    access_cfg = settings.setdefault("access", {})
    stored = (access_cfg.get("current_password") or "").strip()

    if stored and stored.startswith("$2"):
        return False

    plain_source = stored or DEFAULT_SETTINGS["access"]["current_password"] or "admin"
    access_cfg["current_password"] = hash_password(plain_source)
    return True


def _apply_app_config(app):
    """Populate Flask app.config from loaded settings for shared runtime access."""
    if app is None:
        return

    paths_cfg = settings.get("paths", {})
    access_cfg = settings.get("access", {})

    forms_path = (paths_cfg.get("forms_path") or DEFAULT_SETTINGS["paths"]["forms_path"]).strip()
    pdf_path = (paths_cfg.get("pdf_path") or DEFAULT_SETTINGS["paths"]["pdf_path"]).strip()
    admin_password_hash = (access_cfg.get("current_password") or "").strip()

    app.config["FORMS_PATH"] = forms_path
    app.config["PDF_PATH"] = pdf_path
    app.config["ADMIN_PASSWORD_HASH"] = admin_password_hash
    # Backward-compatible key while routes are gradually migrated.
    app.config["ADMIN_PASSWORD"] = admin_password_hash
        
def load_settings(app=None):
    settings_path = os.path.join("settings", "settings.xml")
    print(f"[INFO]: Loading settings from {settings_path}...")
    settings_tree = ET.parse(settings_path)
    settings_root = settings_tree.getroot()
    settings.clear()
        
    for child in settings_root:
        print(child.tag)
        settings[child.tag] = {}
        for subchild in child:
                print(f"    {subchild.tag}: {subchild.text}")
                settings[child.tag][subchild.tag] = subchild.text

    migrated = _ensure_password_hashed()
    if migrated:
        save_settings()

    _apply_app_config(app)

def save_settings():
    settings_path = os.path.join("settings", "settings.xml")
    print(f"[INFO]: Saving settings to {settings_path}...")

    settings_tree = ET.parse(settings_path)
    settings_root = settings_tree.getroot()

    for child in settings_root:
        child_values = settings.get(child.tag, {})
        if not isinstance(child_values, dict):
            continue

        for subchild in child:
            if subchild.tag in child_values:
                value = child_values[subchild.tag]
                subchild.text = "" if value is None else str(value)

    settings_tree.write(settings_path, encoding="utf-8", xml_declaration=True)
    
def create_settings():
    settings_path = os.path.join("settings", "settings.xml")
    print(f"[INFO]: Creating default settings at {settings_path}...")

    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    settings.clear()

    for section, values in DEFAULT_SETTINGS.items():
        settings[section] = dict(values)

    _ensure_password_hashed()

    settings_root = ET.Element("settings")
    for section, values in settings.items():
        section_node = ET.SubElement(settings_root, section)
        for key, value in values.items():
            value_node = ET.SubElement(section_node, key)
            value_node.text = "" if value is None else str(value)

    settings_tree = ET.ElementTree(settings_root)
    settings_tree.write(settings_path, encoding="utf-8", xml_declaration=True)


def sync_app_config(app):
    """Public helper to refresh app.config from current in-memory settings."""
    _apply_app_config(app)