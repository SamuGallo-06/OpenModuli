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


import os
import logging
import xml.etree.ElementTree as ET
import bcrypt

settings = {}
logger = logging.getLogger(__name__)

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
        "primary_color": "#1d4ed8",
        "secondary_color": "#4b5563",
        "background_image": "",
    },
    "access": {
        "current_password": "",
        "new_password": "",
        "confirm_password": "",
    },
}


def get_setting(section: str, key: str, default=None):
    """Return a setting value from the in-memory configuration."""
    section_values = settings.get(section, {})
    if not isinstance(section_values, dict):
        return default
    return section_values.get(key, default)


def _stringify(value, fallback="") -> str:
    if value is None:
        return fallback
    return str(value)


def _ensure_settings_shape():
    for section, values in DEFAULT_SETTINGS.items():
        section_values = settings.setdefault(section, {})
        if not isinstance(section_values, dict):
            section_values = {}
            settings[section] = section_values

        for key in list(section_values.keys()):
            if key not in values:
                del section_values[key]

        for key, default_value in values.items():
            if key not in section_values or section_values[key] in (None, ""):
                section_values[key] = default_value


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

    plain_source = stored or "admin"
    access_cfg["current_password"] = hash_password(plain_source)
    return True


def _settings_file_path() -> str:
    return os.path.join("settings", "settings.xml")


def _apply_app_config(app):
    """Populate Flask app.config from loaded settings for shared runtime access."""
    if app is None:
        return

    _ensure_settings_shape()

    paths_cfg = settings.get("paths", {})
    access_cfg = settings.get("access", {})
    entity_cfg = settings.get("entity", {})
    personalization_cfg = settings.get("personalization", {})
    general_cfg = settings.get("general", {})

    forms_path = _stringify(paths_cfg.get("forms_path") or DEFAULT_SETTINGS["paths"]["forms_path"]).strip()
    pdf_path = _stringify(paths_cfg.get("pdf_path") or DEFAULT_SETTINGS["paths"]["pdf_path"]).strip()
    admin_password_hash = _stringify(access_cfg.get("current_password")).strip()

    app.config["FORMS_PATH"] = forms_path
    app.config["PDF_PATH"] = pdf_path
    app.config["ADMIN_PASSWORD_HASH"] = admin_password_hash
    # Backward-compatible key while routes are gradually migrated.
    app.config["ADMIN_PASSWORD"] = admin_password_hash
    app.config["APP_LANGUAGE"] = _stringify(general_cfg.get("language") or DEFAULT_SETTINGS["general"]["language"]).strip()
    app.config["ENTITY_NAME"] = _stringify(entity_cfg.get("entity_name") or DEFAULT_SETTINGS["entity"]["entity_name"]).strip()
    app.config["ENTITY_LOGO"] = _stringify(entity_cfg.get("logo_image") or DEFAULT_SETTINGS["entity"]["logo_image"]).strip()
    app.config["ENTITY_ADDRESS"] = _stringify(entity_cfg.get("entity_address") or DEFAULT_SETTINGS["entity"]["entity_address"]).strip()
    app.config["ENTITY_CONTACTS"] = _stringify(entity_cfg.get("entity_contacts") or DEFAULT_SETTINGS["entity"]["entity_contacts"]).strip()
    app.config["ENTITY_PHONE"] = _stringify(entity_cfg.get("entity_phone") or DEFAULT_SETTINGS["entity"]["entity_phone"]).strip()
    app.config["PRIMARY_COLOR"] = _stringify(personalization_cfg.get("primary_color") or DEFAULT_SETTINGS["personalization"]["primary_color"]).strip()
    app.config["SECONDARY_COLOR"] = _stringify(personalization_cfg.get("secondary_color") or DEFAULT_SETTINGS["personalization"]["secondary_color"]).strip()
    app.config["BACKGROUND_IMAGE"] = _stringify(personalization_cfg.get("background_image") or DEFAULT_SETTINGS["personalization"]["background_image"]).strip()

    try:
        from pdfutils import set_program_name, set_pdf_path, set_branding

        set_program_name(app.config["ENTITY_NAME"] or "OpenModuli")
        set_pdf_path(app.config["PDF_PATH"])
        set_branding(
            entity_name=app.config["ENTITY_NAME"],
            logo_path=app.config["ENTITY_LOGO"],
            primary_color=app.config["PRIMARY_COLOR"],
            secondary_color=app.config["SECONDARY_COLOR"],
            background_image=app.config["BACKGROUND_IMAGE"],
            contacts=app.config["ENTITY_CONTACTS"],
            address=app.config["ENTITY_ADDRESS"],
            phone=app.config["ENTITY_PHONE"],
        )
    except Exception:
        logger.debug("PDF branding configuration could not be applied", exc_info=True)
        
def load_settings(app=None):
    settings_path = _settings_file_path()
    logger.info("Loading settings from %s", settings_path)

    if not os.path.exists(settings_path):
        create_settings()

    try:
        settings_tree = ET.parse(settings_path)
    except ET.ParseError:
        logger.warning("Settings file is malformed, recreating defaults")
        create_settings()
        settings_tree = ET.parse(settings_path)

    settings_root = settings_tree.getroot()
    settings.clear()

    for child in settings_root:
        settings[child.tag] = {}
        for subchild in child:
            settings[child.tag][subchild.tag] = subchild.text

    _ensure_settings_shape()

    migrated = _ensure_password_hashed()
    if migrated:
        save_settings()

    _apply_app_config(app)

def save_settings():
    settings_path = _settings_file_path()
    logger.info("Saving settings to %s", settings_path)

    os.makedirs(os.path.dirname(settings_path), exist_ok=True)

    if not os.path.exists(settings_path):
        create_settings()

    _ensure_settings_shape()

    settings_root = ET.Element("settings")
    for section, values in DEFAULT_SETTINGS.items():
        section_node = ET.SubElement(settings_root, section)
        current_values = settings.get(section, {})
        for key in values.keys():
            value_node = ET.SubElement(section_node, key)
            value = current_values.get(key, values.get(key)) if isinstance(current_values, dict) else values.get(key)
            value_node.text = "" if value is None else str(value)

    settings_tree = ET.ElementTree(settings_root)

    settings_tree.write(settings_path, encoding="utf-8", xml_declaration=True)
    
def create_settings():
    settings_path = _settings_file_path()
    logger.info("Creating default settings at %s", settings_path)

    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    settings.clear()

    for section, values in DEFAULT_SETTINGS.items():
        settings[section] = dict(values)

    _ensure_password_hashed()
    _ensure_settings_shape()

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


def get_all_settings():
    """Return the full in-memory settings dictionary."""
    return settings