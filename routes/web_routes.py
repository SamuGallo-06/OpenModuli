import os

from flask import abort, redirect, render_template, request, send_from_directory, url_for

from pdfutils import create_pdf_from_form_data
from settings import hash_password, save_settings as persist_settings
from settings import settings as app_settings
from settings import sync_app_config, verify_password
from xmlutils import parse_fxml

from routes.helpers import form_path, normalize_form_name


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

        forms_dir = os.path.join(app.root_path, "forms")
        for file in os.listdir(forms_dir):
            if file.endswith(".fxml"):
                forms.append(os.path.basename(file).split(".")[0])

        return render_template("admin.html", forms=forms)

    @app.route("/admin/settings")
    def settings():
        """@brief Mostra la pagina impostazioni amministrative.

        @return Template HTML settings.
        """
        return render_template("settings.html")

    @app.route("/admin/settings/save", methods=["POST"])
    def save_settings():
        """@brief Placeholder per salvataggio impostazioni da form admin.

        @return Redirect verso la pagina impostazioni.
        """
        return redirect(url_for("settings"))

    @app.route("/admin/settings/change-psswd", methods=["POST"])
    def change_password():
        """@brief Gestisce la richiesta di cambio password amministratore.

        @details
        Verifica password corrente hashata, aggiorna il valore e persiste su XML.

        @return Redirect verso la pagina impostazioni.
        """
        old_password = str(request.form.get("current_password", ""))
        new_password = str(request.form.get("new_password", ""))
        new_password_confirm = str(request.form.get("confirm_password", ""))

        stored_hash = app.config.get("ADMIN_PASSWORD_HASH", "")

        if not verify_password(old_password, stored_hash):
            print("[SETTINGS] Failed to change password: current password is incorrect")
        elif not new_password:
            print("[SETTINGS] Failed to change password: new password is empty")
        elif new_password != new_password_confirm:
            print("[SETTINGS] Failed to change password: new password and confirmation do not match")
        else:
            app_settings.setdefault("access", {})
            app_settings["access"]["current_password"] = hash_password(new_password)
            persist_settings()
            sync_app_config(app)
            print("[SETTINGS] Password changed successfully")

        return redirect(url_for("settings"))

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
            fxml_path = form_path(app.root_path, form_name)
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
        pdf_dir = os.path.join(app.root_path, "pdfs")
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

        dest = form_path(app.root_path, name)
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
