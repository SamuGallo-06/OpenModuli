import os
import re
import tempfile
import xml.etree.ElementTree as ET

from xmlutils import parse_fxml

FORM_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def normalize_form_name(form_name: str) -> str:
    """Normalize and validate a form name."""
    normalized = (form_name or "").strip()
    if not normalized or not FORM_NAME_RE.fullmatch(normalized):
        raise ValueError("Nome modulo non valido")
    return normalized


def form_path(root_path: str, form_name: str) -> str:
    """Build the absolute path of a form from its name."""
    safe_name = normalize_form_name(form_name)
    forms_dir = os.path.join(root_path, "forms")
    return os.path.join(forms_dir, f"{safe_name}.fxml")


def validate_fxml_content(content: str):
    """Validate FXML syntax and semantic parsability."""
    try:
        ET.fromstring(content)
    except ET.ParseError as exc:
        line, column = getattr(exc, "position", (None, None))
        return False, {
            "type": "xml_parse_error",
            "message": str(exc),
            "line": line,
            "column": column,
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
