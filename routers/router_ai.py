from fastapi import APIRouter, Form, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import openai
from pydantic import BaseModel
from db.database import get_db
from datetime import datetime
import os
import tempfile
from typing import Optional
import json
from datetime import datetime

router = APIRouter(tags=["router_AI"])
templates = Jinja2Templates(directory="templates")

# OpenAI API-Key
openai.api_key = '!!!'


class UserText(BaseModel):
    """
    Ein Pydantic-Modell, das den Text repräsentiert, den der Benutzer übermittelt.

    Attribute:
    - userText (str): Der vom Benutzer eingegebene Text.
    """
    userText: str


def parse_date(date_str: str) -> str:
    """
    Diese Funktion versucht, einen Datumsstring in das Format 'YYYY-MM-DD' zu konvertieren.
    Sie unterstützt verschiedene Formate für numerische und sprachliche Datumsangaben, einschließlich deutscher und englischer Monatsnamen.

    Parameter:
    - date_str (str): Der Datumsstring, der geparst werden soll.

    Rückgabewert:
    - str: Das formatierte Datum im 'YYYY-MM-DD'-Format oder der Standardwert '1111-11-11', wenn das Datum nicht erkannt wird.
    """
    date_str = date_str.strip().lower()  # Entfernt Leerzeichen und konvertiert den Text in Kleinbuchstaben

    if date_str == "nicht angegeben":  # Spezieller Fall für 'nicht angegeben'
        return "1111-11-11"

    # Unterstützte Datumsformate (numerisch, deutsch, englisch)
    date_formats = [
        '%d.%m.%Y', '%Y-%m-%d',  # Numerische Formate
        '%d. %B %Y', '%d. %b %Y',  # Deutsche Monatsnamen, lang und kurz
        '%d %B %Y', '%d %b %Y', '%B %d, %Y'  # Englische Monatsnamen, lang und kurz
    ]

    # Deutsche Monatsnamen durch englische Monatsnamen ersetzen
    german_to_english = {
        'januar': 'january', 'februar': 'february', 'märz': 'march', 'mai': 'may',
        'juni': 'june', 'juli': 'july', 'oktober': 'october', 'dezember': 'december',
        'apr.': 'apr', 'aug.': 'aug', 'dez.': 'dec'
    }

    # Ersetzen der deutschen Monatsnamen im Datum
    for german, english in german_to_english.items():
        date_str = date_str.replace(german, english)

    # Versuch, das Datum im angegebenen Format zu parsen
    for date_format in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, date_format)
            return parsed_date.strftime('%Y-%m-%d')  # Gibt das Datum im 'YYYY-MM-DD'-Format zurück
        except ValueError:
            continue

    return "1111-11-11"  # Rückgabe eines Standardwerts, wenn das Parsen fehlschlägt


def extract_data_from_ai_response(response_content: str) -> dict:
    """
    Extrahiert die relevanten Daten aus der Antwort einer KI und formatiert sie in einem Dictionary.

    Die Extraktion basiert auf Schlüsseln wie 'inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value'.

    Parameter:
    - response_content (str): Der Text, der von der KI zurückgegeben wurde.

    Rückgabewert:
    - dict: Ein Dictionary mit den extrahierten Werten.
    """
    data = response_content.strip().split('\n')  # Zerlegt den Text in einzelne Zeilen
    ai_user_data = {}

    for item in data:
        key_value = item.split(':')  # Zerlegt jede Zeile in Schlüssel und Wert
        if len(key_value) == 2:
            key = key_value[0].strip().lower().replace('-', '').strip()  # Normalisiert den Schlüssel
            value = key_value[1].strip()

            # Zuordnung der extrahierten Daten zu den richtigen Schlüsseln
            if 'ort' in key or 'location' in key or 'standort' in key or 'place' in key or 'city' in key:
                key = 'inspection location'
            if 'schiffsname' in key or 'ship' in key:
                key = 'ship name'
            if 'datum' in key or 'date' in key:
                key = 'inspection date'
            if 'details' in key or 'beschreibung' in key or 'erklärung' in key:
                key = 'inspection details'
            if 'numerisch' in key or 'number' in key or 'wert' in key:
                key = 'numerical value'

            ai_user_data[key] = value

    return ai_user_data  # Rückgabe des extrahierten Daten-Dictionary


def request_additional_information(missing_keys: list) -> list:
    """
    Erstellt eine Liste von Fragen basierend auf fehlenden Schlüsseln, um zusätzliche Informationen vom Benutzer anzufordern.

    Parameter:
    - missing_keys (list): Eine Liste von Schlüsseln, für die noch Daten fehlen.

    Rückgabewert:
    - list: Eine Liste von Fragen, die an den Benutzer gestellt werden sollen.
    """
    questions = {
        'inspection location': "Was ist der Standort der Inspektion?",
        'ship name': "Was ist der Name des Schiffes?",
        'inspection date': "Was ist das Datum der Inspektion?",
        'inspection details': "Was sind die Details der Inspektion?",
        'numerical value': "Was ist der numerische Wert?"
    }
    return [questions[key] for key in missing_keys]  # Gibt die Fragen zurück, die den fehlenden Schlüsseln entsprechen


@router.get("/text_input", response_class=HTMLResponse)
async def text_input(request: Request):
    return templates.TemplateResponse("Text-input.html", {"request": request})


@router.post("/process_text", response_class=HTMLResponse)
async def process_text(request: Request, userText: str = Form(...), db: Session = Depends(get_db)):
    """
    Diese Funktion verarbeitet den vom Benutzer eingegebenen Text, sendet ihn an die OpenAI-API und extrahiert die relevanten Daten.

    Parameter:
    - request (Request): Die HTTP-Anfrage mit den Benutzereingaben.
    - userText (str): Der Text, der vom Benutzer eingegeben wurde.
    - db (Session): Eine Datenbanksitzung, die verwendet wird, um auf die Datenbank zuzugreifen (abhängig von FastAPI).

    Ablauf:
    1. Sendet den vom Benutzer eingegebenen Text an das GPT-4-Modell und bittet um Extraktion der relevanten Daten (z.B. 'inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value').
    2. Verarbeitet die Antwort der OpenAI-API und extrahiert die relevanten Daten in ein Dictionary.
    3. Überprüft, ob alle erforderlichen Daten extrahiert wurden. Falls Daten fehlen, fordert es den Benutzer auf, die fehlenden Informationen anzugeben.
    4. Wenn alle Daten vorhanden sind, wird die Antwort im Template "indexAI.html" dargestellt.

    Rückgabewert:
    - HTMLResponse: Stellt entweder die extrahierten Daten oder ein Template zur Ergänzung fehlender Informationen dar.

    Fehlerbehandlung:
    - Bei einem Fehler bei der OpenAI-Anfrage oder der Verarbeitung wird ein HTTP-Fehlerstatus zurückgegeben.
    """
    try:
        # Anfrage an die OpenAI-API, um die relevanten Daten aus dem Text zu extrahieren
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                {"role": "user",
                 "content": f"Extrahiere die relevanten Daten aus dem {userText} basierend auf den Schlüsseln 'inspection location', 'ship name', 'inspection date', 'inspection details' und 'numerical value'. Wenn Informationen zu einem der Schlüssel nicht vorhanden sind, lasse das entsprechende Feld leer."}
            ],
            functions=[
                {
                    "name": "request_additional_information",
                    "description": "Erfordert zusätzliche Informationen vom Benutzer",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "missing_keys": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["missing_keys"]
                    }
                }
            ]
        )

        print("Antwort von OpenAI:", response)

        # Überprüfung, ob eine gültige Antwort von OpenAI empfangen wurde
        if not response or 'choices' not in response or len(response['choices']) == 0:
            raise HTTPException(status_code=500, detail="Keine Antwort von OpenAI erhalten")

        ai_response = response['choices'][0]['message'].get('content')
        if not ai_response:
            raise HTTPException(status_code=500, detail="Die Antwort von OpenAI ist leer")

        # Extraktion der relevanten Daten aus der Antwort von OpenAI
        ai_user_data = extract_data_from_ai_response(ai_response)
        print("Extrahierte Daten von OpenAI:", ai_user_data)

        # Überprüfung auf fehlende Daten
        required_keys = ['inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value']
        missing_keys = [key for key in required_keys if key not in ai_user_data or not ai_user_data[key]]

        # Überprüfung des numerischen Wertes
        if 'numerical value' in ai_user_data:
            try:
                ai_user_data['numerical value'] = float(ai_user_data['numerical value'])
            except ValueError:
                missing_keys.append('numerical value')

        print("missing keys: ", missing_keys)

        # Wenn Daten fehlen, werden die entsprechenden Fragen an den Benutzer gestellt
        if missing_keys:
            questions = request_additional_information(missing_keys)
            return templates.TemplateResponse("missing_data2.html", {"request": request, "questions": questions,
                                                                     "provided_data": json.dumps(ai_user_data)})

        # Datumsformatierung
        if ai_user_data["inspection date"]:
            try:
                formatted_date = parse_date(ai_user_data['inspection date'])
                ai_user_data['inspection date'] = formatted_date
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        # Rückgabe der extrahierten Daten
        return templates.TemplateResponse("indexAI.html", {"request": request, "data": ai_user_data})

    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Anfrage an OpenAI: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Verarbeiten der OpenAI-Antwort: {str(e)}")


@router.get("/process_voice", response_class=HTMLResponse)
async def get_process_voice(request: Request):
    """
    Stellt eine HTML-Seite dar, die es dem Benutzer ermöglicht, eine Audioaufnahme zur Verarbeitung hochzuladen.

    Parameter:
    - request (Request): Die HTTP-Anfrage.

    Rückgabewert:
    - HTMLResponse: Gibt die "Text-input.html"-Seite zurück, auf der der Benutzer die Sprachaufnahme hochladen kann.
    """
    return templates.TemplateResponse("Text-input.html", {"request": request})


@router.post("/process_voice", response_class=HTMLResponse)
async def post_process_voice(request: Request, audioFile: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Diese Funktion verarbeitet eine hochgeladene Audiodatei, konvertiert sie in Text, extrahiert relevante Daten mithilfe der OpenAI-API und gibt diese in einer HTML-Antwort zurück.

    Parameter:
    - request (Request): Die HTTP-Anfrage mit der hochgeladenen Audiodatei.
    - audioFile (UploadFile): Die vom Benutzer hochgeladene Audiodatei.
    - db (Session): Eine Datenbanksitzung, die verwendet wird, um auf die Datenbank zuzugreifen.

    Ablauf:
    1. Die Audiodatei wird in einer temporären Datei gespeichert.
    2. Mithilfe des Whisper-Modells (OpenAI) wird die Audiodatei in Text umgewandelt.
    3. Der transkribierte Text wird an das GPT-4-Modell gesendet, um relevante Daten zu extrahieren, wie z.B. 'inspection location', 'ship name', 'inspection date', 'inspection details', und 'numerical value'.
    4. Falls Daten fehlen, wird der Benutzer aufgefordert, diese zu ergänzen.
    5. Wenn alle erforderlichen Daten vorhanden sind, werden sie in einer HTML-Vorlage angezeigt.

    Rückgabewert:
    - HTMLResponse: Stellt entweder die extrahierten Daten oder eine Seite zur Ergänzung fehlender Informationen dar.

    Fehlerbehandlung:
    - Bei einem Fehler bei der Anfrage an die OpenAI-API oder der Verarbeitung wird ein HTTP-Fehlerstatus zurückgegeben.
    """
    try:
        # Speichert die Audiodatei temporär auf dem Server
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
            temp_audio_file.write(await audioFile.read())
            temp_audio_file_path = temp_audio_file.name

        # Konvertiert die Audiodatei in Text mit OpenAI's Whisper-Modell
        with open(temp_audio_file_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file
            )

        userText = response['text']  # Extrahierter Text aus der Audiodatei

        # Löscht die temporäre Audiodatei
        os.remove(temp_audio_file_path)

        # Anfrage an OpenAI, um die relevanten Daten aus dem Text zu extrahieren
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                {"role": "user",
                 "content": f"Extrahiere die relevanten Daten (location, ship name, date, details, numerical value) aus diesem Text: {userText}"}
            ]
        )

        print("Antwort von OpenAI:", response)  # Debugging-Ausgabe

        # Überprüfung, ob eine gültige Antwort von OpenAI empfangen wurde
        if not response or 'choices' not in response or len(response['choices']) == 0:
            raise HTTPException(status_code=500, detail="Keine Antwort von OpenAI erhalten")

        ai_response = response['choices'][0]['message'].get('content')
        if not ai_response:
            raise HTTPException(status_code=500, detail="Die Antwort von OpenAI ist leer")

        # Verarbeite die Antwort von OpenAI und extrahiere die relevanten Daten
        ai_user_data = extract_data_from_ai_response(ai_response)
        print("Extrahierte Daten von OpenAI:", ai_user_data)  # Debugging-Ausgabe

        # Überprüfen, ob alle erforderlichen Daten extrahiert wurden
        required_keys = ['inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value']
        missing_keys = [key for key in required_keys if key not in ai_user_data or not ai_user_data[key]]

        # Überprüfen, ob der numerische Wert gültig ist
        if 'numerical value' in ai_user_data:
            try:
                ai_user_data['numerical value'] = int(ai_user_data['numerical value'])
            except ValueError:
                missing_keys.append('numerical value')

        # Wenn erforderliche Daten fehlen, werden entsprechende Fragen gestellt
        if missing_keys:
            questions = request_additional_information(missing_keys)
            return templates.TemplateResponse("missing_data2.html", {"request": request, "questions": questions,
                                                                     "provided_data": json.dumps(ai_user_data)})

        # Formatieren des Datumsfeldes
        try:
            formatted_date = parse_date(ai_user_data['inspection date'])
            ai_user_data['inspection date'] = formatted_date
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Rückgabe der extrahierten und formatierten Daten in einer HTML-Vorlage
        return templates.TemplateResponse("indexAI.html", {"request": request, "data": ai_user_data})

    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Anfrage an OpenAI: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Verarbeiten der OpenAI-Antwort: {str(e)}")


@router.post("/complete_data", response_class=HTMLResponse)
async def complete_data(
        request: Request,
        provided_data: str = Form(...),
        missing_data_1: Optional[str] = Form(None),
        missing_data_2: Optional[str] = Form(None),
        missing_data_3: Optional[str] = Form(None),
        missing_data_4: Optional[str] = Form(None),
        missing_data_5: Optional[str] = Form(None),

        audio_missing_data_1: Optional[UploadFile] = File(None),
        audio_missing_data_2: Optional[UploadFile] = File(None),
        audio_missing_data_3: Optional[UploadFile] = File(None),
        audio_missing_data_4: Optional[UploadFile] = File(None),
        audio_missing_data_5: Optional[UploadFile] = File(None)
):
    """
    Diese Funktion verarbeitet fehlende Daten (Text oder Audio) von einem Benutzer und fügt sie zu bereits bereitgestellten Daten hinzu. Sie kombiniert sowohl textliche als auch sprachbasierte Eingaben und gibt die vollständigen Daten als HTML-Seite zurück.

    Parameter:
    - request (Request): Die HTTP-Anfrage mit den Formulareingaben.
    - provided_data (str): JSON-codierte Daten, die bereits bereitgestellt wurden.
    - missing_data_1 bis missing_data_5 (Optional[str]): Optionale Formulardaten, die vom Benutzer als Text bereitgestellt wurden.
    - audio_missing_data_1 bis audio_missing_data_5 (Optional[UploadFile]): Optionale Sprachdateien, die vom Benutzer hochgeladen wurden.

    Ablauf:
    1. Die bereitgestellten Daten werden geladen und fehlende Textdaten und Audiodaten vom Benutzer werden ergänzt.
    2. Audiodaten werden mithilfe von OpenAI's Whisper-Modell in Text umgewandelt.
    3. Die fehlenden Informationen werden in die bereitgestellten Daten integriert.
    4. Die vervollständigten Daten werden im Template "indexAI.html" dargestellt.

    Rückgabewert:
    - HTMLResponse: Gibt die vervollständigten und bereinigten Daten als HTML-Seite zurück.

    Fehlerbehandlung:
    - JSON-Dekodierungsfehler: Wird ausgelöst, wenn die bereitgestellten Daten ungültig sind.
    - OpenAI-Fehler: Wird ausgelöst, wenn ein Fehler bei der Anfrage an OpenAI auftritt.
    - Allgemeine Fehler: Wird ausgelöst, wenn andere Probleme bei der Verarbeitung der Daten auftreten.
    """
    try:
        # Debug-Ausgabe: Zeigt die rohen bereitgestellten Daten und fehlenden Daten an
        print("Bereitgestellte Daten (raw):", provided_data)
        print("Fehlende Daten:", missing_data_1, missing_data_2, missing_data_3, missing_data_4)

        # Versuch, die bereitgestellten Daten als JSON zu dekodieren
        try:
            provided_data = json.loads(provided_data)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Fehler beim Dekodieren der bereitgestellten Daten: {str(e)}")

        # Definieren der erforderlichen Schlüssel
        required_keys = ['inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value']
        missing_keys = [key for key in required_keys if key not in provided_data or not provided_data[key]]

        # Textlich bereitgestellte Daten
        missing_data = [
            missing_data_1,
            missing_data_2,
            missing_data_3,
            missing_data_4,
            missing_data_5
        ]
        missing_data = [data for data in missing_data if data is not None]

        # Sprachlich bereitgestellte Daten (Audio)
        audio_missing_data = [
            audio_missing_data_1,
            audio_missing_data_2,
            audio_missing_data_3,
            audio_missing_data_4,
            audio_missing_data_5
        ]
        audio_missing_data = [data for data in audio_missing_data if data is not
        None]

        # Debug-Ausgabe der bereitgestellten und fehlenden Daten
        print("Bereitgestellte Daten (raw):", provided_data)
        print("Fehlende Daten:", missing_data)

        # Vervollständigung der bereitgestellten Daten mit den fehlenden Textdaten
        for key, value in zip(missing_keys, missing_data):
            if value:
                provided_data[key] = value.strip()

        # Verarbeitung und Vervollständigung mit fehlenden Audiodaten
        for key, audio_file in zip(missing_keys, audio_missing_data):
            if audio_file:
                # Temporäre Datei für die Audiodatei erstellen
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
                    temp_audio_file.write(await audio_file.read())
                    temp_audio_file_path = temp_audio_file.name

                # Audiodatei mit Whisper transkribieren
                with open(temp_audio_file_path, "rb") as audio:
                    response = openai.Audio.transcribe(
                        model="whisper-1",
                        file=audio
                    )

                # Temporäre Audiodatei löschen
                os.remove(temp_audio_file_path)

                # Transkribierten Text zur bereitgestellten Daten hinzufügen
                provided_data[key] = response['text'].strip()

        # Bereinigung der bereitgestellten Daten (z.B. Entfernen von doppelten Sternchen)
        for key in provided_data:
            if isinstance(provided_data[key], str):
                provided_data[key] = provided_data[key].replace('**', '').strip()

        # Überprüfung, ob alle erforderlichen Schlüssel vorhanden sind
        for key in required_keys:
            if key not in provided_data or not provided_data[key]:
                raise HTTPException(status_code=400, detail=f"Fehlender Wert für {key}")

        # Datumsformatierung der bereitgestellten Daten
        try:
            formatted_date = parse_date(provided_data['inspection date'])
            provided_data['inspection date'] = formatted_date
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Debug-Ausgabe der kombinierten und bereinigten Daten
        print("Kombinierte und bereinigte Daten:", provided_data)

        # Rückgabe der vervollständigten Daten als HTML-Seite
        return templates.TemplateResponse("indexAI.html", {"request": request, "data": provided_data})

    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Anfrage an OpenAI: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Verarbeiten der Daten: {str(e)}")
