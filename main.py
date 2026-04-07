import os
from flask import Flask
from rich.console import Console
from time import sleep
from extensions import db, login_manager
from models.user import User
import click

from pdfutils import set_program_name
from routes.fxml_api_routes import register_fxml_api_routes
from routes.server_controls import server_bp
from routes.web_routes import register_web_routes
from settings import *
from utilities.first_start import first_start_setup
from utils import _find_available_port

OPENMODULI_ASCII_ART = r"""   ____                   __  ___          __      ___ 
  / __ \____  ___  ____  /  |/  /___  ____/ /_  __/ (_)
 / / / / __ \/ _ \/ __ \/ /|_/ / __ \/ __  / / / / / / 
/ /_/ / /_/ /  __/ / / / /  / / /_/ / /_/ / /_/ / / /  
\____/ .___/\___/_/ /_/_/  /_/\____/\__,_/\__,_/_/_/   
    /_/                                                """

console = Console()
console.print("[green][INFO][/green] Avvio...")
sleep(2)
console.print()
console.print(OPENMODULI_ASCII_ART, style="cyan bold")
sleep(2)
console.print("[blue][INFO][/blue] Inizializzazione flask...")
sleep(0.5)

app = Flask(__name__)
console.print("[blue][INFO][/blue] Inizializzazione database...")
sleep(0.5)

# Configurazione
app.config['SECRET_KEY'] = 'b7bc08cb7271bf6cd4d6f53a6a9f230f27428971f6e33eea95c33ac853f760cc'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///openmoduli.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

console.print("[blue][INFO][/blue] Inizializzazione login manager...")
sleep(0.5)
login_manager.init_app(app)

# Blueprint
console.print("[blue][INFO][/blue] Inizializzazione blueprint...")
sleep(0.5)
app.register_blueprint(server_bp)

PROGRAM_NAME = "OpenModuli"

# Comandi CLI  ← nuovi
@app.cli.command('init-db')
def init_db():
    """Crea le tabelle nel database."""
    with app.app_context():
        db.create_all()
        click.echo('Database inizializzato.')
        
# Comandi CLI  ← nuovi
@app.cli.command('reset-all-settings-and-user-to-factory-defaults')
def reset_to_factory_defaults():
    """Reimposta tutte le impostazioni e l'utente al valore predefinito."""
    result = console.input("[yellow][ATTENZIONE][/yellow] Questa operazione reimposterà tutte le impostazioni e l'utente amministratore ai valori predefiniti. [red]Procedere? (y/n)[/red] ")
    if(result.lower() != 'y'):
        console.print("[green][INFO][/green] Operazione annullata.")
        return
    
    result = console.input("""[yellow][ATTENZIONE][/yellow] Siete veramente sicuri di voler cancellare tutto?

Questa azione è irreversibile e comporterà la perdita di tutte le impostazioni personalizzate e dell'utente amministratore attuale.
Tutti i moduli e i dati verranno mantenuti, ma sarà necessario riconfigurare l'applicazione e creare un nuovo utente amministratore al prossimo avvio.
[red]Procedere ? (y/n)[/red] """)
    if(result.lower() != 'y'):
        console.print("[green][INFO][/green] Operazione annullata.")
        return
       
    settings_path = os.path.join("settings", "settings.xml")
    if os.path.exists(settings_path):
        os.remove(settings_path)
    with app.app_context():
        db.drop_all()
        db.create_all()
        click.echo('Tutte le impostazioni e l\'utente sono stati reimpostati ai valori predefiniti.')


@app.cli.command('create-admin')
@click.argument('username')
@click.password_option()
def create_admin(username, password):
    """Crea un utente admin."""
    console.print(f"[blue][INFO][/blue] Creazione utente admin '{username}'...")
    sleep(0.5)
    with app.app_context():
        existing = User.query.filter_by(username=username).first()
        if existing:
            click.echo(f'Errore: utente "{username}" esiste già.')
            console.print(f"[red][ERRORE][/red] L'utente '{username}' esiste già.")
            return
        user = User()
        user.username = username
        user.role = 'admin'
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f'Admin "{username}" creato.')
        console.print(f"[green][SUCCESSO][/green] Utente admin '{username}' creato con successo.")

def open_moduli_init():
    console.print("[blue][INFO][/blue] Caricamento della configurazione in corso...")
    sleep(0.5)
    load_settings(app)
    with app.app_context():
        db.create_all()
    if settings.get("general", {}).get("first_access", "true") == "true":
        console.print("[blue][INFO][/blue] Prima configurazione rilevata, avvio procedura guidata...")
        sleep(0.5)
        first_start_setup(app)
        load_settings(app)
    program_name = settings.get("entity", {}).get("entity_name") or PROGRAM_NAME
    set_program_name(program_name)
    console.print("[blue][INFO][/blue] Caricamento delle rotte del server...")
    sleep(0.5)
    register_web_routes(app)
    console.print("[blue][INFO][/blue] Caricamento delle rotte API...")
    sleep(0.5)
    register_fxml_api_routes(app)
    
if __name__ == "__main__":
    console.print("[green][INFO][/green] Avvio...")
    sleep(2)
    open_moduli_init()
    requested_port = int(os.environ.get("PORT", "5000"))
    port = _find_available_port(requested_port)
    app.run(debug=True, port=port)