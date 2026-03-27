# Specifica del formato `.fxml`
**Versione:** 0.1 (draft)
**Autore:** —
**Ultima modifica:** 2026-03-25

---

## Panoramica

`.fxml` (Form XML) è un formato basato su XML per la definizione di moduli online compilabili, con supporto a variabili, espressioni Python e generazione di PDF compatti. Il formato è pensato per essere generato da un editor visuale e interpretato da un backend Python.

---

## Struttura generale

```xml
<?xml version="1.0" encoding="UTF-8"?>
<form id="..." title="..." lang="it" version="1.0">

  <!-- 1. Variabili e formule (opzionale) -->
  <variables> ... </variables>

  <!-- 2. Contenuto: sezioni, righe, campi, condizionali, pagebreak -->
  <section title="...">
    <row> ... </row>
    <conditional if="..."> ... </conditional>
    <pagebreak />
  </section>

</form>
```

Il documento è un singolo file XML con encoding UTF-8. L'elemento radice è sempre `<form>`.

---

## Elemento radice `<form>`

| Attributo | Tipo     | Obbligatorio | Descrizione                              |
|-----------|----------|--------------|------------------------------------------|
| `id`      | stringa  | sì           | Identificatore univoco del modulo        |
| `title`   | stringa  | sì           | Titolo del modulo (usato nel PDF)        |
| `lang`    | BCP 47   | no           | Lingua del modulo. Default: `it`         |
| `version` | stringa  | no           | Versione del modulo. Default: `1.0`      |
| `author`  | stringa  | no           | Autore/ente del modulo                   |

---

## Blocco `<variables>`

Definisce variabili calcolate tramite espressioni Python. Le variabili sono valutate **in ordine** e possono dipendere l'una dall'altra. Sono disponibili automaticamente le variabili di sistema descritte di seguito.

```xml
<variables>
  <var name="eta" expr="today.year - birthday.year" />
  <var name="maggiorenne" expr="eta >= 18" />
</variables>
```

### Attributi di `<var>`

| Attributo | Tipo    | Obbligatorio | Descrizione                          |
|-----------|---------|--------------|--------------------------------------|
| `name`    | stringa | sì           | Nome della variabile                 |
| `expr`    | stringa | sì           | Espressione Python da valutare       |

### Variabili di sistema predefinite

| Nome     | Tipo           | Descrizione                              |
|----------|----------------|------------------------------------------|
| `today`  | `datetime.date`| Data odierna                             |
| `now`    | `datetime.datetime` | Data e ora attuali                  |

I nomi dei campi del modulo (attributo `name`) sono disponibili come variabili Python nel contesto di valutazione. Esempio: un campo `<datefield name="birthday" />` è accessibile come `birthday` (oggetto `datetime.date`).

### Tipi restituiti

Le espressioni possono restituire: `str`, `int`, `float`, `bool`, `datetime.date`. Qualsiasi altro tipo viene convertito con `str()`.

---

## Layout: `<section>` e `<row>`

### `<section>`

Raggruppa logicamente più righe. Nel PDF viene resa come blocco con titolo opzionale.

```xml
<section title="Dati anagrafici">
  <row> ... </row>
</section>
```

| Attributo | Tipo    | Obbligatorio | Descrizione                    |
|-----------|---------|--------------|--------------------------------|
| `title`   | stringa | no           | Titolo visibile della sezione  |

Le sezioni possono essere annidate. Un `<section>` senza `title` è puramente logico.

### `<row>`

Una riga orizzontale di elementi. Può contenere `<text>`, `<printvar>`, campi di input, o combinazioni di essi. Gli elementi sono disposti in sequenza orizzontale; la larghezza di ciascuno è gestita dall'editor.

```xml
<row>
  <text>Nato a</text>
  <textfield name="birth_city" label="Comune (Provincia)" required="true" />
  <text>il</text>
  <datefield name="birthday" label="Data di nascita" required="true" />
</row>
```

---

## Elemento `<text>`

Testo statico inline all'interno di una riga. Non è un campo compilabile.

```xml
<text>Io Sottoscritto</text>
```

Il contenuto è il testo da mostrare. Supporta la sintassi `$variabile` per l'interpolazione:

```xml
<text>Età calcolata: $eta anni</text>
```

## Elemento `<printvar>`

Mostra inline il valore di una variabile o di un campo già acquisito, utile in frasi di riepilogo.

```xml
<text>Il/La sottoscritto/a</text><printvar name="nome" /><printvar name="cognome" />
```

| Attributo | Tipo    | Obbligatorio | Descrizione                                |
|-----------|---------|--------------|--------------------------------------------|
| `name`    | stringa | sì           | Nome della variabile/campo da stampare     |

Nel backend, `<printvar>` non è un input: è un nodo di output/interpolazione.

---

## Campi di input

Tutti i campi condividono questi attributi comuni:

| Attributo     | Tipo    | Obbligatorio | Descrizione                                      |
|---------------|---------|--------------|--------------------------------------------------|
| `name`        | stringa | sì           | Identificatore univoco nel modulo                |
| `label`       | stringa | no           | Etichetta visibile (nell'editor e nel PDF)       |
| `required`    | bool    | no           | Se `true`, il campo è obbligatorio. Default: `false` |
| `default`     | stringa | no           | Valore predefinito                               |
| `placeholder` | stringa | no           | Testo suggerimento (solo editor, non nel PDF)    |
| `readonly`    | bool    | no           | Campo non modificabile dall'utente. Default: `false` |
| `width`       | stringa | no           | Larghezza relativa nella riga (`auto`, `1`, `2`…) |

### `<textfield>` — Testo breve

```xml
<textfield name="name" label="Nome" required="true" placeholder="Mario" />
```

Attributi aggiuntivi:

| Attributo   | Tipo    | Descrizione                              |
|-------------|---------|------------------------------------------|
| `maxlength` | intero  | Numero massimo di caratteri              |
| `pattern`   | regex   | Espressione regolare di validazione      |
| `error_msg` | stringa | Messaggio in caso di validazione fallita |

### `<textarea>` — Testo lungo

```xml
<textarea name="note" label="Note aggiuntive" rows="4" />
```

Attributi aggiuntivi:

| Attributo | Tipo   | Descrizione                         |
|-----------|--------|-------------------------------------|
| `rows`    | intero | Altezza iniziale in righe. Default: `3` |

### `<numberfield>` — Numero

```xml
<numberfield name="importo" label="Importo (€)" min="0" max="99999" step="0.01" />
```

Attributi aggiuntivi:

| Attributo | Tipo  | Descrizione                         |
|-----------|-------|-------------------------------------|
| `min`     | float | Valore minimo                        |
| `max`     | float | Valore massimo                       |
| `step`    | float | Incremento. Default: `1`            |

### `<datefield>` — Data

```xml
<datefield name="birthday" label="Data di nascita" required="true" />
```

Attributi aggiuntivi:

| Attributo | Tipo | Descrizione                                        |
|-----------|------|----------------------------------------------------|
| `min`     | data | Data minima selezionabile (`YYYY-MM-DD`)           |
| `max`     | data | Data massima selezionabile (`YYYY-MM-DD`)          |
| `format`  | stringa | Formato di visualizzazione nel PDF. Default: `DD/MM/YYYY` |

Il valore è disponibile nelle espressioni Python come oggetto `datetime.date`.

### `<selectfield>` — Menu a tendina

```xml
<selectfield name="stato_civile" label="Stato civile" required="true">
  <option value="celibe">Celibe/Nubile</option>
  <option value="coniugato">Coniugato/a</option>
  <option value="divorziato">Divorziato/a</option>
  <option value="vedovo">Vedovo/a</option>
</selectfield>
```

Ogni `<option>` ha un `value` (usato internamente) e un testo visibile (contenuto del tag).

### `<checkfield>` — Casella di spunta

```xml
<checkfield name="privacy" label="Acconsento al trattamento dei dati personali" required="true" />
```

Il valore nelle espressioni Python è `True` o `False`.

### `<radiogroup>` — Scelta esclusiva

```xml
<radiogroup name="sesso" label="Sesso">
  <option value="M">Maschio</option>
  <option value="F">Femmina</option>
  <option value="altro">Altro</option>
</radiogroup>
```

### `<computed>` — Campo calcolato (sola lettura)

Mostra il valore di una variabile come campo non compilabile.

```xml
<computed name="eta_display" label="Età" value="$eta" />
```

| Attributo | Tipo    | Obbligatorio | Descrizione                         |
|-----------|---------|--------------|-------------------------------------|
| `value`   | stringa | sì           | Espressione `$variabile` da mostrare |

---

## `<conditional>` — Blocco condizionale

Mostra o nasconde un blocco di righe in base a una condizione.

```xml
<conditional if="$maggiorenne">
  <row>
    <textfield name="patente" label="Numero patente" />
  </row>
</conditional>

<conditional if="not $maggiorenne">
  <row>
    <textfield name="tutore" label="Nome del tutore legale" required="true" />
  </row>
</conditional>
```

| Attributo | Tipo    | Obbligatorio | Descrizione                                              |
|-----------|---------|--------------|----------------------------------------------------------|
| `if`      | stringa | sì           | Condizione: `$variabile` o espressione Python booleana   |

La condizione è valutata lato backend. Nell'editor visuale, i blocchi condizionali vengono visualizzati/nascosti in tempo reale al variare dei campi.

Un `<conditional>` può contenere `<row>`, `<section>`, altri `<conditional>`, o `<pagebreak>`.

---

## `<pagebreak>` — Interruzione di pagina

Forza un'interruzione di pagina nel PDF generato. Non ha effetti sull'editor visuale (che scorre verticalmente).

```xml
<pagebreak />
```

Nessun attributo. Può comparire ovunque nel corpo del modulo, anche dentro `<section>` o `<conditional>`.

---

## Interpolazione di variabili nel testo

La sintassi `$nome` sostituisce la variabile `nome` con il suo valore calcolato. Può essere usata in:

- Contenuto di `<text>`
- Attributo `default` dei campi
- Attributo `value` di `<computed>`

Esempio:

```xml
<text>Gentile $name $surname,</text>
```

Per includere un `$` letterale, usare `$$`.

---

## Validazione dei campi

La validazione può essere inline (attributi del campo) o tramite blocco `<validate>` figlio:

```xml
<textfield name="cf" label="Codice Fiscale" required="true">
  <validate pattern="[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]"
            message="Codice fiscale non valido" />
</textfield>
```

| Attributo | Tipo    | Descrizione                              |
|-----------|---------|------------------------------------------|
| `pattern` | regex   | Espressione regolare (Python `re`)       |
| `message` | stringa | Messaggio di errore da mostrare          |
| `expr`    | stringa | Espressione Python arbitraria (bool)     |

Con `expr` si possono fare validazioni incrociate tra campi:

```xml
<textfield name="data_fine" label="Data fine">
  <validate expr="data_fine > data_inizio" message="La data di fine deve essere successiva a quella di inizio" />
</textfield>
```

---

## Esempio completo

```xml
<?xml version="1.0" encoding="UTF-8"?>
<form id="dichiarazione_residenza" title="Dichiarazione di residenza" lang="it" version="1.0" author="Comune di Esempio">

  <variables>
    <var name="eta" expr="today.year - birthday.year" />
    <var name="maggiorenne" expr="eta >= 18" />
  </variables>

  <section title="Dati anagrafici">
    <row>
      <text>Io Sottoscritto/a</text>
      <textfield name="name" label="Nome" required="true" />
      <textfield name="surname" label="Cognome" required="true" />
    </row>
    <row>
      <text>Nato/a a</text>
      <textfield name="birth_city" label="Comune (Provincia)" required="true" />
      <text>il</text>
      <datefield name="birthday" label="Data di nascita" required="true" />
    </row>
    <row>
      <textfield name="cf" label="Codice Fiscale" required="true">
        <validate pattern="[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]"
                  message="Codice fiscale non valido" />
      </textfield>
    </row>
  </section>

  <conditional if="not $maggiorenne">
    <row>
      <textfield name="tutore" label="Nome del tutore legale" required="true" />
    </row>
  </conditional>

  <pagebreak />

  <section title="Residenza">
    <row>
      <textfield name="via" label="Via/Piazza" required="true" width="2" />
      <textfield name="civico" label="N°" required="true" width="1" />
    </row>
    <row>
      <textfield name="comune" label="Comune" required="true" />
      <textfield name="provincia" label="Provincia" required="true" maxlength="2" />
      <textfield name="cap" label="CAP" required="true" maxlength="5" />
    </row>
  </section>

  <pagebreak />

  <section title="Dichiarazione finale">
    <row>
      <text>Il sottoscritto dichiara che le informazioni fornite sono veritiere.</text>
    </row>
    <row>
      <checkfield name="privacy" label="Acconsento al trattamento dei dati personali ai sensi del GDPR" required="true" />
    </row>
  </section>

</form>
```

---

## Note implementative (backend)

- Il contesto Python per la valutazione delle espressioni deve essere **sandboxato** (es. `restrictedpython` o `ast.literal_eval` per espressioni semplici).
- I valori dei campi devono essere convertiti nel tipo corretto prima di essere iniettati nel contesto: `datefield` → `datetime.date`, `numberfield` → `int`/`float`, `checkfield` → `bool`.
- Le variabili in `<variables>` sono valutate **solo dopo** che tutti i campi hanno un valore (o al cambio di un campo nell'editor).
- I `<conditional>` con `if` falso **non** devono essere inclusi nel PDF né validati.

---

## Versioning

Il campo `version` dell'elemento `<form>` segue il formato `MAJOR.MINOR`. Il parser deve rifiutare documenti con `MAJOR` diverso dalla versione supportata.

---

*Specifica soggetta a modifiche. Versione draft.*
