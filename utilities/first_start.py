from settings import *
from rich.console import Console
from rich.prompt import Prompt
import os
from extensions import db
from models.user import User

from time import sleep


def first_start_setup(app):
    console = Console()
    console.clear()
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
        console.print("[bold blue]CONFIGURAZIONE GUIDATA OPEN MODULI[/bold blue]")
        console.print("[bold]_________________________________________________________________[/bold]")
        console.print()
        console.print("Benvenuto in Open Moduli!")
        console.print(
            "Questa procedura guidata ti aiuterà a configurare le impostazioni iniziali del programma, "
            "inclusa la creazione di un utente amministratore."
        )
        console.print()
        console.print("Verranno richieste le seguenti informazioni:")
        console.print("  [cyan]•[/cyan] Nome dell'organizzazione")
        console.print("  [cyan]•[/cyan] Credenziali dell'account amministratore")
        console.print("  [cyan]•[/cyan] Percorsi di salvataggio per moduli e PDF")
        console.print()
        console.print("[dim]Puoi interrompere la procedura in qualsiasi momento con Ctrl+C.[/dim]")
        console.print("[bold]_________________________________________________________________[/bold]")
        console.print()

        user_input = console.input("[bold]Premere [green]INVIO[/green] per continuare o [red]Q[/red] per uscire: [/bold]").strip().lower()
        if user_input == "q":
            console.print("[yellow]Configurazione annullata. Uscita...[/yellow]")
            exit(0)
        
        # procedura di configurazione
        break

    while True:
        console.clear()
        console.print("[bold blue]CONFIGURAZIONE GUIDATA OPEN MODULI[/bold blue]")
        console.print("[bold]_________________________________________________________________[/bold]")
        console.print()
        console.print("Impostazione utente amministratore.")
        console.print()
        console.print(
            "Immettere ora i dati per l'account amministratore che utilizzerai per accedere al pannello di controllo."
            "Questo account avrà privilegi completi, quindi scegli una password sicura."
        )
        admin_username = Prompt.ask("[cyan]- Nome utente[/cyan]: ", default="admin").strip()
        if not admin_username:
            console.print("[bold red][ERRORE][/bold red] Lo username non puo essere vuoto.")
            continue
        break

    while True:
        admin_password = Prompt.ask("[cyan]- Password[/cyan]", password=True).strip()
        confirm_password = Prompt.ask("[cyan]- Conferma password[/cyan]", password=True).strip()

        if not admin_password:
            console.clear()
            console.print("[bold blue]CONFIGURAZIONE GUIDATA OPEN MODULI[/bold blue]")
            console.print("[bold]_________________________________________________________________[/bold]")
            console.print()
            console.print("Impostazione utente amministratore.")
            console.print()
            console.print("[bold red][ERRORE][/bold red] La password non puo essere vuota.")
            continue

        if admin_password != confirm_password:
            console.clear()
            console.print("[bold blue]CONFIGURAZIONE GUIDATA OPEN MODULI[/bold blue]")
            console.print("[bold]_________________________________________________________________[/bold]")
            console.print()
            console.print("Impostazione utente amministratore.")
            console.print()
            console.print("[bold red][ERRORE][/bold red] Le password non coincidono. Riprova.")
            continue

        settings["access"]["current_password"] = hash_password(admin_password)
        break
    
    while True:
        console.clear()
        console.print("[bold blue]CONFIGURAZIONE GUIDATA OPEN MODULI[/bold blue]")
        console.print("[bold]_________________________________________________________________[/bold]")
        console.print()
        console.print("Impostazione dati dell'organizzazione.")
        console.print()
        console.print(
            "Immettere ora i dati dell'organizzazione che userà qusta copia di Open Moduli."
            "Queste informazioni saranno visibili nei moduli e nei PDF generati."
            "Il nome dell'organizzazione è obbligatorio, mentre gli altri campi sono facoltativi ma consigliati per una migliore personalizzazione."
        )
        entity_name = Prompt.ask("[cyan]- Nome dell'ente[/cyan]: ").strip()
        if not entity_name:
            console.clear()
            console.print("[bold blue]CONFIGURAZIONE GUIDATA OPEN MODULI[/bold blue]")
            console.print("[bold]_________________________________________________________________[/bold]")
            console.print()
            console.print("Impostazione dati dell'organizzazione.")
            console.print()
            console.print("[bold red][ERRORE][/bold red] Il nome dell'organizzazione non puo essere vuoto.")
            continue
        settings["entity"]["entity_name"] = entity_name
        
        entity_address = Prompt.ask("[cyan]- Indirizzo[/cyan]: ").strip()
        entity_email = Prompt.ask("[cyan]- Email[/cyan]: ").strip()
        entity_phone = Prompt.ask("[cyan]- Telefono[/cyan]: ").strip()
        
        break
    
    while True:
        console.clear()
        console.print("[bold blue]CONFIGURAZIONE GUIDATA OPEN MODULI[/bold blue]")
        console.print("[bold]_________________________________________________________________[/bold]")
        console.print()
        console.print("Impostazione percorsi di salvataggio.")
        console.print()
        console.print(
            "Immettere ora il percorso di salvataggio per i moduli FXML e per i PDF generati. "
            "Lascia vuoto per usare i valori predefiniti (forms/ per i moduli e pdfs/ per i PDF)."
        )
        
        pdf_path = Prompt.ask("[cyan]- Percorso PDF[/cyan]: ").strip()
        if not pdf_path:
            pdf_path = "pdfs/"
        settings["paths"]["pdf_path"] = pdf_path

        form_path = Prompt.ask("[cyan]- Percorso Moduli[/cyan]: ").strip()
        if not form_path:
            form_path = "forms/"
        settings["paths"]["forms_path"] = form_path

        break
    
    with app.app_context():
        console.clear()
        console.print("[bold blue]CONFIGURAZIONE GUIDATA OPEN MODULI[/bold blue]")
        console.print("[bold]_________________________________________________________________[/bold]")
        console.print()
        console.print("[bold blue][INFO][/bold blue] Creazione utente amministratore in corso...", end="")
        sleep(0.5)
        db.create_all()
        existing_admin = User.query.filter_by(username=admin_username).first()
        if existing_admin:
            existing_admin.set_password(admin_password)
            existing_admin.role = "admin"
        else:
            new_admin = User()
            new_admin.username = admin_username
            new_admin.role = "admin"
            new_admin.set_password(admin_password)
            db.session.add(new_admin)
        db.session.commit()
        console.print("[bold green][INFO][/bold green] Fatto!", end="")
        sleep(0.5)
    
    console.print("[bold blue][INFO][/bold blue] Salvataggio della configurazione in corso...", end="")
    
    settings["entity"]["entity_address"] = entity_address
    settings["entity"]["entity_contacts"] = entity_email
    settings["entity"]["entity_phone"] = entity_phone
    settings["general"]["first_access"] = "false"
    
    console.print("[bold green][INFO][/bold green] Fatto!", end="")
    
    console.print("[bold blue][INFO][/bold blue] Applicazione delle modifiche...", end="")
    save_settings()
    console.print("[bold green][INFO][/bold green] Fatto!", end="")
    sleep(2)
    
    console.clear()
    console.print("[bold blue]CONFIGURAZIONE GUIDATA OPEN MODULI[/bold blue]")
    console.print("[bold]_________________________________________________________________[/bold]")
    console.print()
    console.print("[blue][INFO][/blue] Prima configurazione completata con successo.")
    console.input("[dim]Premi un tasto per continuare...[/dim]")


