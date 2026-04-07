import os

from flask import Flask
from rich.console import Console

from pdfutils import set_program_name
from routes.fxml_api_routes import register_fxml_api_routes
from routes.server_controls import server_bp
from routes.web_routes import register_web_routes
from settings import *
from utilities.first_start import first_start_setup
from utils import _find_available_port

app = Flask(__name__)
app.register_blueprint(server_bp)

PROGRAM_NAME = "OpenModuli"

console = Console()

OPENMODULI_ASCII_ART = r"""
    ,----..                                            ____
   /   /   \\                                         ,'  , `.
  /   .     : ,-.----.                            ,-+-,.' _ |
 .   /   ;.  \\    /  \                ,---,   ,-+-. ;   , ||   ,---.      ,---.'|         ,--, |  | :   ,--.'|
.   ;   /  ` ;|   :    |           ,-+-. /  | ,--.'|'   |  ;|  '   ,'\     |   | :       ,'_ /| :  : '   |  |,
;   |  ; \ ; ||   | .\ :   ,---.  ,--.'|'   ||   |  ,', |  ': /   /   |    |   | |  .--. |  | : |  ' |   `--'_
|   :  | ; | '.   : |: |  /     \|   |  ,"' ||   | /  | |  ||.   ; ,. :  ,--.__| |,'_ /| :  . | '  | |   ,' ,'|
.   |  ' ' ' :|   |  \ : /    /  |   | /  | |'   | :  | :  |,'   | |: : /   ,'   ||  ' | |  . . |  | :   '  | |
'   ;  \; /  ||   : .  |.    ' / |   | |  | |;   . |  ; |--' '   | .; :.   '  /  ||  | ' |  | | '  : |__ |  | :
 \   \  ',  / :     |`-' '   ;   /|   | |  |/ |   : |  | ,    |   :    |'   ; |:  |:  | : ;  ; | |  | '.'|'  : |__
  ;   :    /  :   : :    |   |  / |   | |--'  |   : '  |/      \   \  / |   | '/  ''  :  `--'   \;  :    ;|  | '.'|
   \   \ .'   |   | :    |   :    |   |/      ;   | |`-'        `----'  |   :    :|:  ,      .-./|  ,   / ;  :    ;
    `---`     `---'.|     \   \  /'---'       |   ;/                     \   \  /   `--`----'     ---`-'  |  ,   /
                `---`      `----'             '---'                       `----'                           ---`-'
"""

def open_moduli_init():
    console.print("[green][INFO][/green] Avvio...")
    load_settings(app)
    if settings.get("general", {}).get("first_access", "true") == "true":
        console.print("[blue][INFO][/blue] Prima configurazione rilevata, avvio procedura guidata...")
        first_start_setup()

    load_settings(app)
    program_name = settings.get("entity", {}).get("entity_name") or PROGRAM_NAME
    set_program_name(program_name)
    console.print("[blue][INFO][/blue] Caricamento delle rotte del server...")
    register_web_routes(app)
    console.print("[blue][INFO][/blue] Caricamento delle rotte API...")
    register_fxml_api_routes(app)

    console.print("[green][INFO][/green] Avvio completato.")
    console.print()
    console.print(OPENMODULI_ASCII_ART, style="cyan bold")

if __name__ == "__main__":
    open_moduli_init()    
    requested_port = int(os.environ.get("PORT", "5000"))
    port = _find_available_port(requested_port)
    app.run(debug=True, port=port)