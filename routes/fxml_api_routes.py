import os

from flask import abort, jsonify, request, url_for

from utils import _json_safe
from xmlutils import extract_runtime_outputs, parse_fxml

from routes.helpers import form_path_from_dir, normalize_form_name, resolve_forms_dir, validate_fxml_content


def register_fxml_api_routes(app):
    @app.route("/api/form/<form_name>/runtime", methods=["POST"])
    def form_runtime(form_name: str):
        try:
            forms_dir = resolve_forms_dir(app.root_path, app.config.get("FORMS_PATH"))
            fxml_path = form_path_from_dir(forms_dir, form_name)
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

    @app.route("/api/fxml/forms", methods=["GET"])
    def api_list_fxml_forms():
        forms_dir = resolve_forms_dir(app.root_path, app.config.get("FORMS_PATH"))
        forms = []

        if os.path.isdir(forms_dir):
            for file in os.listdir(forms_dir):
                if file.endswith(".fxml"):
                    forms.append(os.path.basename(file).split(".")[0])

        forms.sort()
        return jsonify({"forms": forms})

    @app.route("/api/fxml/forms/<form_name>", methods=["GET"])
    def api_read_fxml_form(form_name: str):
        try:
            forms_dir = resolve_forms_dir(app.root_path, app.config.get("FORMS_PATH"))
            path = form_path_from_dir(forms_dir, form_name)
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
            safe_name = normalize_form_name(form_name)
            forms_dir = resolve_forms_dir(app.root_path, app.config.get("FORMS_PATH"))
            destination = form_path_from_dir(forms_dir, safe_name)
        except ValueError:
            return jsonify({"error": "Nome modulo non valido"}), 400

        valid, details = validate_fxml_content(content)
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

        valid, details = validate_fxml_content(content)
        status = 200 if valid else 400
        return jsonify({"valid": valid, "error": details}), status
