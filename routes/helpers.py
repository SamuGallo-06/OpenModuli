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
import re
import tempfile
import xml.etree.ElementTree as ET

from xmlutils import parse_fxml

FORM_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def normalize_form_name(form_name: str) -> str:
    """Normalize and validate a form name."""
    normalized = (form_name or "").strip()
    normalized = normalized.replace(" ", "_")
    normalized = normalized.replace(".", "_")
    normalized = normalized.replace("/", "_")
    normalized = normalized.replace("\\", "_")
    normalized = normalized.lower()
    if not normalized or not FORM_NAME_RE.fullmatch(normalized):
        raise ValueError("Nome modulo non valido")
    return normalized


def form_path(root_path: str, form_name: str, forms_dir: str | None = None) -> str:
    """Build the absolute path of a form from its name.

    The forms directory can be overridden by a configured path relative to the
    application root. The helper still protects against path traversal by
    validating the logical form name.
    """
    safe_name = normalize_form_name(form_name)
    resolved_forms_dir = forms_dir or os.path.join(root_path, "forms")
    return os.path.join(resolved_forms_dir, f"{safe_name}.fxml")


def resolve_forms_dir(root_path: str, configured_forms_path: str | None = None) -> str:
    """Resolve the absolute forms directory from a configured relative path."""
    relative_path = (configured_forms_path or "forms").strip() or "forms"
    return os.path.join(root_path, relative_path)


def form_path_from_dir(forms_dir: str, form_name: str) -> str:
    """Resolve a form path inside an already resolved forms directory."""
    safe_name = normalize_form_name(form_name)
    return os.path.join(forms_dir, f"{safe_name}.fxml")


def validate_fxml_content(content: str):
    """Validate FXML syntax and semantic parsability."""
    xml_root = None
    try:
        xml_root = ET.fromstring(content)
    except ET.ParseError as exc:
        line, column = getattr(exc, "position", (None, None))
        return False, {
            "type": "xml_parse_error",
            "message": str(exc),
            "line": line,
            "column": column,
        }

    if xml_root is not None:
        script_nodes = xml_root.findall(".//script")
        if len(script_nodes) > 1:
            return False, {
                "type": "semantic_error",
                "message": "Ogni modulo puo contenere al massimo un nodo <script>.",
            }

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".fxml", encoding="utf-8", delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        parse_fxml(temp_path, {})
        return True, None
    except Exception as exc:
        return False, {
            "type": "semantic_error",
            "message": str(exc),
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
