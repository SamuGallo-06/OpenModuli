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
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

from flask import abort, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from extensions import db, mail
from models.user import User
from pdfutils import create_pdf_from_form_data
from settings import get_all_settings, save_settings as persist_settings
from settings import settings as app_settings
from settings import sync_app_config
from xmlutils import parse_fxml
from email_utils import send_email, send_email_with_attachment, build_email_body

from routes.helpers import form_path_from_dir, normalize_form_name, resolve_forms_dir
from rich.console import Console

import logging
logger = logging.getLogger(__name__)

console = Console()

def init():
    global console
    console = Console()
    console.print("[blue][INFO][/blue] Web routes module initialized")
    
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


def _save_background_image(app, file_storage) -> str:
    """Save background image as user/background.jpeg under project root."""
    if not file_storage or not getattr(file_storage, "filename", ""):
        return ""

    user_dir = os.path.join(app.root_path, "user")
    os.makedirs(user_dir, exist_ok=True)
    destination = os.path.join(user_dir, "background.jpeg")
    file_storage.save(destination)
    return os.path.relpath(destination, app.root_path)


def _extract_module_script_path(fxml_path: str) -> str:
    """Return the full script path under forms/scripts for a form, if present."""
    try:
        root = ET.parse(fxml_path).getroot()
    except ET.ParseError:
        return ""

    script_node = root.find(".//script")
    if script_node is None:
        return ""

    script_file = (script_node.get("file") or "").strip()
    if not script_file:
        return ""

    forms_dir = os.path.dirname(fxml_path)
    script_name = os.path.basename(script_file)
    return os.path.join(forms_dir, "scripts", script_name)


def _run_module_script(app, form_name: str, script_path: str, submitted_values: dict) -> str:
    """Run the form-linked script and return a non-blocking warning message on failure."""
    if not script_path:
        return ""

    if not os.path.exists(script_path):
        warning = f"Script non trovato per il modulo '{form_name}': {script_path}"
        app.logger.warning("[FORM] %s", warning)
        return warning

    payload = {
        "form_name": form_name,
        "values": submitted_values,
    }

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
        if result.stdout.strip():
            app.logger.info("[FORM] Output script '%s': %s", script_path, result.stdout.strip())
        return ""
    except subprocess.TimeoutExpired:
        warning = "Lo script associato al modulo ha superato il tempo massimo (10s)."
        app.logger.warning("[FORM] %s Script: %s", warning, script_path)
        return warning
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        warning = "Lo script associato al modulo ha restituito un errore."
        if stderr:
            warning = f"{warning} Dettaglio: {stderr}"
        app.logger.warning("[FORM] Script fallito '%s': %s", script_path, stderr or "errore sconosciuto")
        return warning
    except Exception as exc:  # pragma: no cover - safeguard branch
        warning = f"Errore durante l'esecuzione dello script associato: {exc}"
        app.logger.warning("[FORM] %s", warning)
        return warning


def _open_folder_in_file_manager(path: str) -> bool:
    """Try to open a folder with the OS graphical file manager."""
    if not os.path.isdir(path):
        return False

    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
            return True

        if sys.platform == "darwin":
            subprocess.Popen(["open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True

        # Linux and other POSIX desktops
        if os.name == "posix":
            if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
                return False
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception:
        return False

    return False


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

    @app.route("/user/<path:filename>")
    def user_asset(filename: str):
        """Serve files from the project user directory."""
        user_dir = os.path.join(app.root_path, "user")
        return send_from_directory(user_dir, filename)

    @app.route("/admin")
    @login_required
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

        return render_template(
            "admin.html", 
            forms=forms,
        )
    
    @app.route("/admin/open_pdf_folder")
    @login_required
    def open_pdf_folder():
        """@brief Apre la cartella PDF nel file manager grafico del sistema.

        @return Redirect ad admin in caso di apertura riuscita, oppure alla pagina lista PDF.

        @details
        Prova ad aprire la cartella su Windows/Linux/macOS. Se non disponibile
        (ambiente headless, comando assente o errore), mostra un elenco browser dei PDF.
        """
        pdf_dir = os.path.join(app.root_path, app.config.get("PDF_PATH", "pdfs"))

        if _open_folder_in_file_manager(pdf_dir):
            return redirect(url_for("admin", message="Cartella PDF aperta nel file manager", message_type="success"))
        console.print("[green][ACTION][/green] Attempt to open PDF folder in file manager failed, showing PDF list in browser instead")
        return redirect(url_for("pdf_files_browser", message="Apertura grafica non disponibile: mostro elenco file", message_type="warning"))

    @app.route("/admin/pdfs")
    @login_required
    def pdf_files_browser():
        """Show generated PDF files in a browser-friendly list."""
        pdf_dir = os.path.join(app.root_path, app.config.get("PDF_PATH", "pdfs"))
        files = []

        if os.path.isdir(pdf_dir):
            for entry in os.listdir(pdf_dir):
                file_path = os.path.join(pdf_dir, entry)
                if not os.path.isfile(file_path):
                    continue
                if not entry.lower().endswith(".pdf"):
                    continue

                stat = os.stat(file_path)
                files.append(
                    {
                        "name": entry,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                    }
                )

        files.sort(key=lambda item: item["mtime"], reverse=True)
        console.print("[green][ACTION][/green] PDF files listed for browser download")
        return render_template(
            "pdf_files.html",
            files=files,
            pdf_dir=pdf_dir,
            message=request.args.get("message", ""),
            message_type=request.args.get("message_type", ""),
        )

    @app.route("/admin/settings")
    @login_required
    def settings():
        """@brief Mostra la pagina impostazioni amministrative.

        @return Template HTML settings.
        """
        return render_template("settings.html", **_template_message_context())

    @app.route("/admin/settings/save", methods=["POST"])
    @login_required
    def save_settings():
        """@brief Salva le impostazioni amministrative nel file XML.

        @return Redirect verso la pagina impostazioni.
        """
        app_settings.setdefault("general", {})
        app_settings.setdefault("paths", {})
        app_settings.setdefault("entity", {})
        app_settings.setdefault("personalization", {})
        app_settings.setdefault("email", {})
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
        app_settings["email"]["server"] = (request.form.get("email_server", "") or "").strip()
        app_settings["email"]["port"] = (request.form.get("email_port", "587") or "587").strip() or "587"
        app_settings["email"]["use_ssl"] = "true" if request.form.get("email_use_ssl") == "true" else "false"
        app_settings["email"]["use_tls"] = "true" if request.form.get("email_use_tls") == "true" else "false"
        app_settings["email"]["username"] = (request.form.get("email_username", "") or "").strip()
        app_settings["email"]["password"] = (request.form.get("email_password", "") or "").strip()
        app_settings["email"]["default_sender"] = (request.form.get("email_default_sender", "") or "").strip()

        logo_path = _save_uploaded_asset(app, request.files.get("logo_image"), os.path.join("static", "uploads", "branding"))
        background_path = _save_background_image(app, request.files.get("background_image"))

        if logo_path:
            app_settings["entity"]["logo_image"] = logo_path
        if background_path:
            app_settings["personalization"]["background_image"] = background_path

        persist_settings()
        sync_app_config(app)
        console.print("[green][ACTION][/green] Settings saved by admin user '%s'", current_user.username)
        return redirect(url_for("settings", message="Impostazioni salvate con successo", message_type="success"))

    @app.route("/admin/settings/change-psswd", methods=["POST"])
    @login_required
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

        message = "Password aggiornata con successo"
        message_type = "success"

        db_user = User.query.get(current_user.id)
        if db_user is None:
            console.print("[red][ERROR][/red] Failed to change password: user session is stale")
            message = "Sessione utente non valida"
            message_type = "error"
        elif not db_user.check_password(old_password):
            console.print("[red][ERROR][/red] Failed to change password: current password is incorrect")
            message = "Password corrente non valida"
            message_type = "error"
        elif not new_password:
            console.print("[red][ERROR][/red] Failed to change password: new password is empty")
            message = "La nuova password non puo essere vuota"
            message_type = "error"
        elif new_password != new_password_confirm:
            console.print("[red][ERROR][/red] Failed to change password: new password and confirmation do not match")
            message = "La nuova password e la conferma non coincidono"
            message_type = "error"
        else:
            db_user.set_password(new_password)
            db.session.commit()
            console.print("[green][ACTION][/green] Password changed successfully")

        return redirect(url_for("settings", message=message, message_type=message_type))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """@brief Mostra il login admin e valida la password in POST.

        @return Template login (GET), login con errore, oppure redirect ad admin.
        """
        if current_user.is_authenticated:
            return redirect(url_for("admin"))

        if request.method == "POST":
            username = (request.form.get("username", "") or "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if not user or not user.is_active or not user.check_password(password):
                console.print("[red][ERROR][/red] Failed login attempt for user '%s'", username)
                return render_template("login.html", error="Invalid password")
            login_user(user, remember=True)
            console.print("[green][ACTION][/green] User logged in successfully: '%s'", username)
            return redirect(url_for("admin"))

    @app.route("/logout", methods=["GET"])
    @login_required
    def logout():
        logout_user()
        console.print("[yellow][LOGOUT][/yellow] User logged out successfully: '%s'", current_user.username)
        return redirect(url_for("login"))

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
            script_warning = ""
            email_warning = ""

            ## Executing associated script if defined in the form
            script_path = _extract_module_script_path(fxml_path)
            if script_path:
                app.logger.info("[FORM] A script was found attached to '%s': %s", form_name, script_path)
                console.print("[blue][INFO][/blue] A script was found attached to form '%s': %s", form_name, script_path)
                console.print("[green][ACTION][/green] Executing script attached to form '%s'", form_name)
                script_warning = _run_module_script(app, form_name, script_path, submitted_values)
            else:
                console.print("[blue][INFO][/blue] No script attached to form '%s'", form_name)
                app.logger.info("[FORM] No script attached to '%s'", form_name)
            console.print("[green][ACTION][/green] Form submitted successfully: '%s'", form_name)
            ## Generating PDF result from submitted form data
            pdf_result = create_pdf_from_form_data(
                form_name,
                form_attributes,
                nodes,
                submitted_values,
            )

            # Extract submitter metadata (fields declared in the template, not in the FXML)
            submitter_name = submitted_values.get("nome_compilante") or form_data.get("nome_compilante")
            submitter_surname = submitted_values.get("cognome_compilante") or form_data.get("cognome_compilante")
            submitter_email = submitted_values.get("email_compilante") or form_data.get("email_compilante")

            # Ensure values are available in form_data for downstream use (PDF, email, logs)
            if submitter_name is not None:
                form_data["nome_compilante"] = submitter_name
            if submitter_surname is not None:
                form_data["cognome_compilante"] = submitter_surname
            if submitter_email is not None:
                form_data["email_compilante"] = submitter_email

            entity_name = app.config.get('ENTITY_NAME', 'OpenModuli')
            subject = f"[{entity_name} tramite OpenModuli] Conferma ricezione modulo"
            email_body = build_email_body(submitter_name, submitter_surname, form_name, entity_name)
            pdf_path = pdf_result["pdf_path"]
            print("=== EMAIL DEBUG ===")
            print(f"SERVER: '{app.config.get('MAIL_SERVER')}'")
            print(f"PORT: {app.config.get('MAIL_PORT')} ({type(app.config.get('MAIL_PORT'))})")
            print(f"USE_SSL: {app.config.get('MAIL_USE_SSL')}")
            print(f"USE_TLS: {app.config.get('MAIL_USE_TLS')}")
            print(f"USERNAME: '{app.config.get('MAIL_USERNAME')}'")
            print("==================")

            email_sent, email_error = send_email_with_attachment(mail, subject, [submitter_email], email_body, pdf_path)
            if not email_sent:
                email_warning = "L'email di conferma non e stata inviata."
                if email_error:
                    app.logger.warning("[FORM] Email send failed for '%s': %s", form_name, email_error)

            return render_template(
                "form_result.html",
                form_name=form_name,
                form_attributes=form_attributes,
                pdf_result=pdf_result,
                script_warning=script_warning,
                email_warning=email_warning,
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
        console.print("[green][ACTION][/green] PDF download requested: %s", filename)
        pdf_dir = os.path.join(app.root_path, app.config.get("PDF_PATH", "pdfs"))
        return send_from_directory(pdf_dir, filename, as_attachment=True)

    @app.route("/upload_form", methods=["POST"])
    @login_required
    def upload_form():
        """@brief Carica un file FXML e lo salva nella directory moduli.

        @return Redirect verso l'anteprima del modulo caricato.

        @details
        Valida nome logico modulo e verifica estensione `.fxml`.
        """
        file = request.files["fxml_file"]
        console.print("[green][ACTION][/green] Uploading '%s'...", file.filename, end="")
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
        console.print("[green]Done![/green]")
        return redirect(url_for("form_view", form_name=name))

    @app.route("/create_form", methods=["GET", "POST"])
    @login_required
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
                filename = normalize_form_name(name)
        except ValueError:
            filename = ""

        return render_template("form_creator.html", form_name=name, form_filename=filename)

    @app.route("/about/license")
    def license_view():
        """@brief Espone il file LICENSE del progetto.

        @return Contenuto testuale della licenza.
        """
        return send_from_directory(app.root_path, "LICENSE", mimetype="text/plain")
