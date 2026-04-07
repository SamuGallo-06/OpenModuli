# TODO integrazione impostazioni caricate

## main.py
- [X] Chiamare `open_moduli_init()` prima di avviare il server (ora e definita ma non invocata).
- [ ] Dopo `load_settings()`, copiare in `app.config` i valori utili (es. `ADMIN_PASSWORD`, `FORMS_PATH`, `PDF_PATH`, `LANGUAGE`, colori tema, dati ente).
- [ ] Impostare `PROGRAM_NAME` da impostazioni (`entity.entity_name`) con fallback a `OpenModuli`.
- [ ] Passare a `set_program_name(...)` il nome effettivo preso dalle impostazioni.

## settings.py
- [ ] Aggiungere funzioni helper di accesso sicuro, ad esempio `get_setting(section, key, default=None)`.
- [ ] Gestire il caso file XML assente o malformato con fallback senza crash.
- [ ] Introdurre validazione e casting tipi per chiavi note (boolean, path, colore).
- [ ] Normalizzare i path (`forms_path`, `pdf_path`) in formato coerente.
- [ ] Evitare `print` diretti e usare logging strutturato.

## routes/web_routes.py
- [ ] Usare `app.config["FORMS_PATH"]` al posto del path hardcoded `forms` in `admin()`.
- [ ] Usare `app.config["PDF_PATH"]` in `download_generated_pdf()`.
- [ ] In `settings()`, passare il dizionario impostazioni al template per precompilare il form.
- [ ] In `save_settings()`, leggere i campi POST, aggiornare `settings`, chiamare `save_settings()` del modulo impostazioni, poi ricaricare config in `app.config`.
- [ ] In `change_password()`, usare la password persistita nelle impostazioni e salvarla davvero su XML quando cambia.
- [ ] Rendere configurabile lingua e branding nelle pagine renderizzate (titolo, nome ente, logo).

## routes/fxml_api_routes.py
- [ ] Usare `app.config["FORMS_PATH"]` per leggere/salvare i file FXML (ora usa path fisso via root_path/forms).
- [ ] Validare che il path configurato esista e sia scrivibile prima del salvataggio.
- [ ] Se usi impostazioni di lingua, localizzare i messaggi di errore JSON.

## routes/helpers.py
- [ ] Far accettare a `form_path(...)` la directory forms da config invece di assumere sempre `forms`.
- [ ] Aggiungere helper per risolvere path in modo sicuro (no path traversal) anche con directory configurabili.

## pdfutils.py
- [ ] Usare il path PDF configurato (`PDF_PATH`) invece della cartella hardcoded locale in `_ensure_pdfs_dir()`.
- [ ] Applicare colori configurati (`primary_color`, `secondary_color`) agli stili PDF.
- [ ] Inserire metadati ente (nome, contatti) nel footer/header se presenti nelle impostazioni.

## templates/settings.html
- [ ] Precompilare tutti gli input con i valori correnti delle impostazioni (`value=...`).
- [ ] Mostrare anteprima per logo e background se configurati.
- [ ] Uniformare i nomi campi del form alla struttura XML (`general`, `paths`, `entity`, `personalization`, `access`).
- [ ] Aggiungere feedback di salvataggio/errore (flash message o banner).

## templates/partials/footer.html
- [ ] Mostrare nome ente e contatti da impostazioni invece di testo statico.

## templates/index.html
- [ ] Mostrare branding dinamico (nome ente/logo) letto dalle impostazioni.

## static/admin.js
- [ ] Aggiornare eventuali chiamate API/form submit per includere i campi impostazioni effettivi.
- [ ] Gestire risposta di successo/errore dal salvataggio impostazioni con messaggi utente.

## static/style.css
- [ ] Introdurre variabili CSS alimentate dalle impostazioni (colore primario/secondario).
- [ ] Prevedere fallback quando i colori non sono definiti.

## settings/settings.xml
- [ ] Ripulire il blocco `access`: mantenere solo i dati persistenti necessari (es. password hash), rimuovendo `new_password` e `confirm_password` che non dovrebbero essere salvati.
- [ ] Definire valori di default non vuoti per i campi minimi richiesti.
- [ ] Valutare migrazione da password in chiaro a hash.

## Priorita consigliata
- [ ] 1) Bootstrap configurazione (`main.py` + `settings.py`)
- [ ] 2) Percorsi dinamici (`routes/web_routes.py` + `routes/fxml_api_routes.py` + `routes/helpers.py` + `pdfutils.py`)
- [ ] 3) Salvataggio impostazioni da UI (`templates/settings.html` + `routes/web_routes.py` + `static/admin.js`)
- [ ] 4) Branding/tema (`templates/*` + `static/style.css`)
- [ ] 5) Hardening sicurezza password (`settings/settings.xml` + logica cambio password)
