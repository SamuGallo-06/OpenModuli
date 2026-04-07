from settings import *
from rich.console import Console
from rich.prompt import Prompt
import os


def first_start_setup():
    console = Console()
    console.print("[blue][INFO][/blue] Preparazione alla configurazione iniziale...")
    settings_path = os.path.join("settings", "settings.xml")

    if not os.path.exists(settings_path):
        create_settings()
    else:
        load_settings()

    settings.setdefault("general", {})
    settings.setdefault("access", {})
    settings.setdefault("entity", {})

    while True:
        admin_password = Prompt.ask("[cyan]Imposta password amministratore[/cyan]", password=True).strip()
        confirm_password = Prompt.ask("[cyan]Conferma password amministratore[/cyan]", password=True).strip()

        if not admin_password:
            console.print("[bold red][ERRORE][/bold red] La password non puo essere vuota.")
            continue

        if admin_password != confirm_password:
            console.print("[bold red][ERRORE][/bold red] Le password non coincidono. Riprova.")
            continue

        settings["access"]["current_password"] = hash_password(admin_password)
        break
    
    while True:
        entity_name = Prompt.ask("[cyan]Nome dell'ente[/cyan]").strip()
        if not entity_name:
            console.print("[bold red][ERRORE][/bold red] Il nome dell'ente non puo essere vuoto.")
            continue
        settings["entity"]["entity_name"] = entity_name
        break
    
    settings["general"]["first_access"] = "false"
    save_settings()
    console.print("[blue][INFO][/blue] Prima configurazione completata con successo.")
    console.input("[dim]Premi un tasto per continuare...[/dim]")


