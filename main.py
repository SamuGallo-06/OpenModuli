from flask import (
    Flask, render_template, request, abort, redirect, url_for, jsonify, send_from_directory
)
import os
import re
import tempfile
import xml.etree.ElementTree as ET

from xmlutils import parse_fxml, extract_runtime_outputs
from utils import _json_safe, _find_available_port
from pdfutils import create_pdf_from_form_data, set_program_name

from routes.server_controls import server_bp
from settings import *

app = Flask(__name__)
app.register_blueprint(server_bp)


PROGRAM_NAME = "OpenModuli"
FORM_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

PASSWORD = "admin"

set_program_name(PROGRAM_NAME)


def _normalize_form_name(form_name: str) -> str:
    """Normalize and validate a form name.
    
    Removes leading/trailing whitespace from the provided form name and validates
    it against the FORM_NAME_RE regex pattern. The normalized name must be non-empty
    and match the expected format.
    
    @param form_name (str): The form name to normalize. Can be None or empty string.
    @return (str): The normalized form name stripped of whitespace.
    @raises ValueError: If the form name is empty after stripping or does not match
                        the FORM_NAME_RE regex pattern. Error message: "Nome modulo non valido"
    """
    normalized = (form_name or "").strip()
    if not normalized or not FORM_NAME_RE.fullmatch(normalized):
        raise ValueError("Nome modulo non valido")
    return normalized


def _form_path(form_name: str) -> str:
    """@brief Constructs the file path for a form FXML file based on the form name.

    @param form_name (str): The name of the form to locate.

    @return (str): The full file path to the form's FXML file located in the application's forms directory.

    @details This function normalizes the provided form name and constructs a path
             to the corresponding FXML file in the application's forms directory.
    """
    safe_name = _normalize_form_name(form_name)
    forms_dir = os.path.join(app.root_path, "forms")
    return os.path.join(forms_dir, f"{safe_name}.fxml")

@app.route("/")
def index():
    """_summary_
    First page, shows a welcome message and links to the admin page.

    Returns:
        _type_: _description_
    """
    return render_template("index.html")

@app.route("/admin")
def admin():
    """_summary_
    ## Admin page
    This is the admin page
    
    - Form Manager: it lists all the available forms and allows to create new ones or upload existing ones.
    - Settings: it allows to change some settings of the application (not implemented yet).

    Returns:
        _type_: _description_
    """
    forms = []

    for file in os.listdir("forms"):
        if file.endswith(".fxml"):
            forms.append(os.path.basename(file).split(".")[0])
    
    return render_template(
        "admin.html",
        forms=forms
    )
    
@app.route("/admin/settings")
def settings():
    """_summary_
    ## Settings page
    This is the settings page, where the admin can change some settings of the application (not implemented yet).

    Returns:
        _type_: _description_
    """
    return render_template("settings.html")

@app.route("/admin/settings/save", methods=["POST"])
def save_settings():
    return redirect(url_for("settings"))

@app.route("/admin/settings/change-psswd", methods=["POST"])
def change_password():
    global PASSWORD
    old_password = str(request.form.get("current_password", ""))
    new_password = str(request.form.get("new_password", ""))
    new_password_confirm = str(request.form.get("confirm_password", ""))
    
    if((old_password == PASSWORD) and (new_password == new_password_confirm)):
        print("[SETTINGS] Password changed successfully")
    elif old_password != PASSWORD:
        print("[SETTINGS] Failed to change password: current password is incorrect")
    elif new_password != new_password_confirm:
        print("[SETTINGS] Failed to change password: new password and confirmation do not match")
    else:
        print("[SETTINGS] Failed to change password: unknown error")
    
    
    return redirect(url_for("settings"))

@app.route("/login", methods=["GET", "POST"])
def login():
    """_summary_
    ## Login page
    This is the login page, where the admin can log in to access the admin panel.

    Returns:
        _type_: _description_
    """
    if request.method == "POST":
        password = request.form.get("password", "")
        otp_code = request.form.get("otp-code", "")
        if password != PASSWORD:
            return render_template("login.html", error="Invalid password")
        return redirect(url_for("admin"))
    
    return render_template("login.html")

@app.route("/form/<form_name>", methods=["GET", "POST"])
def form_view(form_name: str):
    """Loads a form from a file and shows it on the web page.

    Args:
        form_name (str): The name of the form to display. It should correspond to an FXML file in the forms directory, without the extension.

    Returns:
        render_template: HTML page rendering the form view.
    """
    try:
        fxml_path = _form_path(form_name)
    except ValueError:
        abort(404)
    
    if not os.path.exists(fxml_path):
        abort(404)
        
    submitted_values = request.form.to_dict() if request.method == "POST" else request.args.to_dict()
    form_attributes, nodes, variables, form_data, conditionals, variable_defs = parse_fxml(fxml_path, submitted_values)
    
    # If this is a form submission (POST), generate PDF
    pdf_result = None
    if request.method == "POST":
        pdf_result = create_pdf_from_form_data(
            form_name,
            form_attributes,
            nodes,
            submitted_values,
        )
    
        return render_template(
            "form_result.html",
            form_name=form_name,
            form_attributes=form_attributes,
            pdf_result=pdf_result,
        )
    
    return render_template(
        "form_view.html",
        form_name=form_name,
        form_attributes=form_attributes,
        nodes=nodes,
        variables=variables,
        form_data=form_data,
        conditionals=conditionals,
        variable_defs=variable_defs,
        runtime_url=url_for("form_runtime", form_name=form_name),
    )

@app.route("/api/form/<form_name>/runtime", methods=["POST"])
def form_runtime(form_name: str):
    try:
        fxml_path = _form_path(form_name)
    except ValueError:
        abort(404)

    if not os.path.exists(fxml_path):
        abort(404)

    payload = request.get_json(silent=True) or {}
    submitted_values = payload.get("values", {})

    _, nodes, variables, _, _, _ = parse_fxml(fxml_path, submitted_values)
    runtime_outputs = extract_runtime_outputs(nodes)

    return jsonify(
        {
            "variables": _json_safe(variables),
            "printvars": _json_safe(runtime_outputs["printvars"]),
            "computed": _json_safe(runtime_outputs["computed"]),
        }
    )


@app.route("/pdfs/<path:filename>", methods=["GET"])
def download_generated_pdf(filename: str):
    pdf_dir = os.path.join(app.root_path, "pdfs")
    return send_from_directory(pdf_dir, filename, as_attachment=True)

@app.route("/upload_form", methods=["POST"])
def upload_form():
    file = request.files["fxml_file"]
    try:
        name = _normalize_form_name(request.form["name"])
    except ValueError:
        abort(400)

    uploaded_name = (file.filename or "").lower()
    if not uploaded_name.endswith(".fxml"):
        abort(400)
    
    dest = _form_path(name)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    file.save(dest)
    
    return redirect(url_for("form_view", form_name=name))

@app.route("/create_form", methods=["GET", "POST"])
def create_form():
    name = ""

    if request.method == "POST":
        name = request.form.get("new-form-name", "")
    else:
        name = request.args.get("name", "")

    try:
        if name:
            name = _normalize_form_name(name)
    except ValueError:
        name = ""
    
    return render_template(
        "form_creator.html", 
        form_name=name
    )


@app.route("/api/fxml/forms", methods=["GET"])
def api_list_fxml_forms():
    forms_dir = os.path.join(app.root_path, "forms")
    forms = []

    for file in os.listdir(forms_dir):
        if file.endswith(".fxml"):
            forms.append(os.path.basename(file).split(".")[0])

    forms.sort()
    return jsonify({"forms": forms})


@app.route("/api/fxml/forms/<form_name>", methods=["GET"])
def api_read_fxml_form(form_name: str):
    try:
        path = _form_path(form_name)
    except ValueError:
        return jsonify({"error": "Nome modulo non valido"}), 400

    if not os.path.exists(path):
        return jsonify({"error": "Modulo non trovato"}), 404

    with open(path, "r", encoding="utf-8") as source:
        content = source.read()

    return jsonify({"name": form_name, "content": content})


@app.route("/api/fxml/forms/<form_name>", methods=["POST"])
def api_save_fxml_form(form_name: str):
    payload = request.get_json(silent=True) or {}
    content = payload.get("content", "")

    if not isinstance(content, str) or not content.strip():
        return jsonify({"error": "Contenuto FXML mancante"}), 400

    try:
        safe_name = _normalize_form_name(form_name)
        destination = _form_path(safe_name)
    except ValueError:
        return jsonify({"error": "Nome modulo non valido"}), 400

    valid, details = _validate_fxml_content(content)
    if not valid:
        return jsonify({"valid": False, "error": details}), 400

    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8") as target:
        target.write(content)

    return jsonify(
        {
            "saved": True,
            "name": safe_name,
            "preview_url": url_for("form_view", form_name=safe_name),
        }
    )


@app.route("/api/fxml/validate", methods=["POST"])
def api_validate_fxml_form():
    payload = request.get_json(silent=True) or {}
    content = payload.get("content", "")

    if not isinstance(content, str) or not content.strip():
        return jsonify({"valid": False, "error": {"message": "Contenuto FXML mancante"}}), 400

    valid, details = _validate_fxml_content(content)
    status = 200 if valid else 400
    return jsonify({"valid": valid, "error": details}), status

@app.route("/about/license")
def license_view():
    return send_from_directory(app.root_path, "LICENSE", mimetype="text/plain")


def _validate_fxml_content(content: str):
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

if __name__ == "__main__":
    requested_port = int(os.environ.get("PORT", "5000"))
    port = _find_available_port(requested_port)
    app.run(debug=True, port=port)