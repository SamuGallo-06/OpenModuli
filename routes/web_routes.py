import os

from flask import abort, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from pdfutils import create_pdf_from_form_data
from settings import get_all_settings, hash_password, save_settings as persist_settings
from settings import settings as app_settings
from settings import sync_app_config, verify_password
from xmlutils import parse_fxml

from routes.helpers import form_path_from_dir, normalize_form_name, resolve_forms_dir


def _template_message_context() -> dict:
    return {
        "settings_data": get_all_settings(),
        "message": request.args.get("message", ""),
        "message_type": request.args.get("message_type", ""),
    }


def _save_uploaded_asset(app, file_storage, relative_folder: str) -> str:
    if not file_storage or not getattr(file_storage, "filename", ""):
        return ""

    filename = secure_filename(file_storage.filename)
    if not filename:
        return ""

    target_dir = os.path.join(app.root_path, relative_folder)
    os.makedirs(target_dir, exist_ok=True)
    destination = os.path.join(target_dir, filename)
    file_storage.save(destination)
    return os.path.relpath(destination, app.root_path)


def register_web_routes(app):
    """@brief Registra tutte le route web HTML dell'applicazione.

    @param app Istanza Flask su cui registrare gli endpoint.

    @details
    Questa funzione definisce e registra le route orientate alla UI:
    homepage, pannello admin, login, visualizzazione moduli, upload e pagine statiche.
    """

    @app.route("/")
    def index():
        """@brief Renderizza la homepage pubblica.

        @return Template HTML index.
        """
        return render_template("index.html")

    @app.route("/admin")
    def admin():
        """@brief Mostra il pannello amministrativo con i moduli disponibili.

        @return Template HTML admin con la lista dei moduli FXML.
        """
        forms = []

        forms_dir = resolve_forms_dir(app.root_path, app.config.get("FORMS_PATH"))
        if os.path.isdir(forms_dir):
            for file in os.listdir(forms_dir):
                if file.endswith(".fxml"):
                    forms.append(os.path.basename(file).split(".")[0])

        return render_template("admin.html", forms=forms)

    @app.route("/admin/settings")
    def settings():
        """@brief Mostra la pagina impostazioni amministrative.

        @return Template HTML settings.
        """
        return render_template("settings.html", **_template_message_context())

    @app.route("/admin/settings/save", methods=["POST"])
    def save_settings():
        """@brief Salva le impostazioni amministrative nel file XML.

        @return Redirect verso la pagina impostazioni.
        """
        app_settings.setdefault("general", {})
        app_settings.setdefault("paths", {})
        app_settings.setdefault("entity", {})
        app_settings.setdefault("personalization", {})
        app_settings.setdefault("access", {})

        app_settings["general"]["language"] = (request.form.get("language", "it") or "it").strip() or "it"
        app_settings["paths"]["forms_path"] = (request.form.get("forms_path", "forms") or "forms").strip() or "forms"
        app_settings["paths"]["pdf_path"] = (request.form.get("pdf_path", "pdfs") or "pdfs").strip() or "pdfs"
        app_settings["entity"]["entity_name"] = (request.form.get("entity_name", "OpenModuli") or "OpenModuli").strip() or "OpenModuli"
        app_settings["entity"]["entity_address"] = (request.form.get("entity_address", "") or "").strip()
        app_settings["entity"]["entity_contacts"] = (request.form.get("entity_contacts", "") or "").strip()
        app_settings["entity"]["entity_phone"] = (request.form.get("entity_phone", "") or "").strip()
        app_settings["personalization"]["primary_color"] = (request.form.get("primary_color", "") or "").strip()
        app_settings["personalization"]["secondary_color"] = (request.form.get("secondary_color", "") or "").strip()

        logo_path = _save_uploaded_asset(app, request.files.get("logo_image"), os.path.join("static", "uploads", "branding"))
        background_path = _save_uploaded_asset(app, request.files.get("background_image"), os.path.join("static", "uploads", "branding"))

        if logo_path:
            app_settings["entity"]["logo_image"] = logo_path
        if background_path:
            app_settings["personalization"]["background_image"] = background_path

        persist_settings()
        sync_app_config(app)

        return redirect(url_for("settings", message="Impostazioni salvate con successo", message_type="success"))

    @app.route("/admin/settings/change-psswd", methods=["POST"])
    def change_password():
        """@brief Gestisce la richiesta di cambio password amministratore.
urce /path/completo/a/openmoduli/venv/bin/activate
        @details
        Verifica password corrente hashata, aggiorna il valore e persiste su XML.

        @return Redirect verso la pagina impostazioni.
        """
        old_password = str(request.form.get("current_password", ""))
        new_password = str(request.form.get("new_password", ""))
        new_password_confirm = str(request.form.get("confirm_password", ""))

        stored_hash = app.config.get("ADMIN_PASSWORD_HASH", "")

        message = "Password aggiornata con successo"
        message_type = "success"

        if not verify_password(old_password, stored_hash):
            print("[SETTINGS] Failed to change password: current password is incorrect")
            message = "Password corrente non valida"
            message_type = "error"
        elif not new_password:
            print("[SETTINGS] Failed to change password: new password is empty")
            message = "La nuova password non puo essere vuota"
            message_type = "error"
        elif new_password != new_password_confirm:
            print("[SETTINGS] Failed to change password: new password and confirmation do not match")
            message = "La nuova password e la conferma non coincidono"
            message_type = "error"
        else:
            app_settings.setdefault("access", {})
            app_settings["access"]["current_password"] = hash_password(new_password)
            persist_settings()
            sync_app_config(app)
            print("[SETTINGS] Password changed successfully")

        return redirect(url_for("settings", message=message, message_type=message_type))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """@brief Mostra il login admin e valida la password in POST.

        @return Template login (GET), login con errore, oppure redirect ad admin.
        """
        if request.method == "POST":
            password = request.form.get("password", "")
            stored_hash = app.config.get("ADMIN_PASSWORD_HASH", "")
            if not verify_password(password, stored_hash):
                return render_template("login.html", error="Invalid password")
            return redirect(url_for("admin"))

        return render_template("login.html")

    @app.route("/form/<form_name>", methods=["GET", "POST"])
    def form_view(form_name: str):
        """@brief Mostra un modulo FXML o genera il PDF su submit.

        @param form_name Nome del modulo senza estensione.
        @return Template form_view (GET) o form_result (POST).

        @details
        In GET risolve il modulo e renderizza il form dinamico.
        In POST elabora i dati inviati e crea il PDF di riepilogo.
        """
        try:
            forms_dir = resolve_forms_dir(app.root_path, app.config.get("FORMS_PATH"))
            fxml_path = form_path_from_dir(forms_dir, form_name)
        except ValueError:
            abort(404)

        if not os.path.exists(fxml_path):
            abort(404)

        submitted_values = request.form.to_dict() if request.method == "POST" else request.args.to_dict()
        form_attributes, nodes, variables, form_data, conditionals, variable_defs = parse_fxml(fxml_path, submitted_values)

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

    @app.route("/pdfs/<path:filename>", methods=["GET"])
    def download_generated_pdf(filename: str):
        """@brief Scarica un PDF generato precedentemente.

        @param filename Nome file PDF richiesto.
        @return Risposta file come allegato.
        """
        pdf_dir = os.path.join(app.root_path, app.config.get("PDF_PATH", "pdfs"))
        return send_from_directory(pdf_dir, filename, as_attachment=True)

    @app.route("/upload_form", methods=["POST"])
    def upload_form():
        """@brief Carica un file FXML e lo salva nella directory moduli.

        @return Redirect verso l'anteprima del modulo caricato.

        @details
        Valida nome logico modulo e verifica estensione `.fxml`.
        """
        file = request.files["fxml_file"]
        try:
            name = normalize_form_name(request.form["name"])
        except ValueError:
            abort(400)

        uploaded_name = (file.filename or "").lower()
        if not uploaded_name.endswith(".fxml"):
            abort(400)

        forms_dir = resolve_forms_dir(app.root_path, app.config.get("FORMS_PATH"))
        dest = form_path_from_dir(forms_dir, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        file.save(dest)

        return redirect(url_for("form_view", form_name=name))

    @app.route("/create_form", methods=["GET", "POST"])
    def create_form():
        """@brief Apre l'editor/creatore modulo precompilando il nome se fornito.

        @return Template form_creator con nome modulo opzionale.
        """
        name = ""

        if request.method == "POST":
            name = request.form.get("new-form-name", "")
        else:
            name = request.args.get("name", "")

        try:
            if name:
                name = normalize_form_name(name)
        except ValueError:
            name = ""

        return render_template("form_creator.html", form_name=name)

    @app.route("/about/license")
    def license_view():
        """@brief Espone il file LICENSE del progetto.

        @return Contenuto testuale della licenza.
        """
        return send_from_directory(app.root_path, "LICENSE", mimetype="text/plain")
