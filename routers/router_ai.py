from fastapi import APIRouter, Form, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import openai
from pydantic import BaseModel
from db.database import get_db
from datetime import datetime
import locale
import os
import tempfile
from typing import Optional
import json

locale.setlocale(locale.LC_TIME, "de_DE")

router = APIRouter(tags=["router_AI"])
templates = Jinja2Templates(directory="templates")

# OpenAI API-Key
openai.api_key = 'sk-proj-uSLL0VokwK420NRtURgqT3BlbkFJK21oMFYqydJI9jD4qpzR'


class UserText(BaseModel):
    userText: str


def parse_date(date_str):
    if date_str.strip().lower() == "nicht angegeben":
        return "1111-11-11"
    try:
        return datetime.strptime(date_str, '%d.%m.%Y').strftime('%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_str, '%d. %B %Y').strftime('%Y-%m-%d')
        except ValueError:
            raise ValueError("Ungültiges Datumsformat. Bitte verwende 'dd.mm.yyyy' oder 'dd. Monat yyyy'.")


def extract_data_from_ai_response(response_content):
    data = response_content.strip().split('\n')
    ai_user_data = {}
    for item in data:
        key_value = item.split(':')
        if len(key_value) == 2:
            key = key_value[0].strip().lower().replace('-', '').strip()
            value = key_value[1].strip()
            if 'ort' in key or 'location' in key or 'standort' in key or 'place' in key or 'city' in key or 'Stadt' in key:
                key = 'inspection location'
            if 'schiffsname' in key or 'schiffname' in key or 'schiff name' in key or 'ship' in key or 'schiff' in key or 'name of ship' in key or 'name des schiffs' in key:
                key = 'ship name'
            if 'inspektionsdatum' in key or 'datum' in key or 'date' in key:
                key = 'inspection date'
            if 'inspektionsdetails' in key or 'details' in key or 'beschreibung' in key or 'erklärung' in key:
                key = 'inspection details'
            if 'numerischer wert' in key or 'nummer' in key or 'number' in key or 'numerical' in key or 'numerische' in key or 'numerisch' in key:
                key = 'numerical value'
            ai_user_data[key] = value
    return ai_user_data


def request_additional_information(missing_keys):
    questions = {
        'inspection location': "Was ist der Standort der Inspektion?",
        'ship name': "Was ist der Name des Schiffes?",
        'inspection date': "Was ist das Datum der Inspektion?",
        'inspection details': "Was sind die Details der Inspektion?",
        'numerical value': "Was ist der numerische Wert?"
    }
    return [questions[key] for key in missing_keys]


@router.get("/text_input", response_class=HTMLResponse)
async def text_input(request: Request):
    return templates.TemplateResponse("Text-input.html", {"request": request})


@router.post("/process_text", response_class=HTMLResponse)
async def process_text(request: Request, userText: str = Form(...), db: Session = Depends(get_db)):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                {"role": "user",
                 "content": f"Extrahiere die relevanten Daten(location, ship name, date, details, numerical value) aus diesem Text: {userText}"}
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

        if not response or 'choices' not in response or len(response['choices']) == 0:
            raise HTTPException(status_code=500, detail="Keine Antwort von OpenAI erhalten")

        ai_response = response['choices'][0]['message'].get('content')
        if not ai_response:
            raise HTTPException(status_code=500, detail="Die Antwort von OpenAI ist leer")

        ai_user_data = extract_data_from_ai_response(ai_response)
        print("Extrahierte Daten von OpenAI:", ai_user_data)

        required_keys = ['inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value']
        missing_keys = [key for key in required_keys if key not in ai_user_data or not ai_user_data[key]]
        print("test", missing_keys)
        if missing_keys:
            questions = request_additional_information(missing_keys)
            return templates.TemplateResponse("missing_data.html", {"request": request, "questions": questions,
                                                                    "provided_data": json.dumps(ai_user_data)})
        if ai_user_data["inspection date"]:
            try:
                formatted_date = parse_date(ai_user_data['inspection date'])
                ai_user_data['inspection date'] = formatted_date
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        return templates.TemplateResponse("indexAI.html", {"request": request, "data": ai_user_data})

    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Anfrage an OpenAI: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Verarbeiten der OpenAI-Antwort: {str(e)}")


@router.get("/process_voice", response_class=HTMLResponse)
async def get_process_voice(request: Request):
    return templates.TemplateResponse("Text-input.html", {"request": request})


@router.post("/process_voice", response_class=HTMLResponse)
async def post_process_voice(request: Request, audioFile: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        # Temporäre Datei für die Audiodatei erstellen
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
            temp_audio_file.write(await audioFile.read())
            temp_audio_file_path = temp_audio_file.name

        # Audiodatei in Text konvertieren (mit Whisper-1 Speech-to-Text-Service)
        with open(temp_audio_file_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file
            )

        userText = response['text']

        # Löschen der temporären Audiodatei
        os.remove(temp_audio_file_path)

        # Anfrage an OpenAI stellen
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                {"role": "user",
                 "content": f"Extrahiere die relevanten Daten (location, ship name, date, details, numerical value) aus diesem Text: {userText}"}
            ]
        )

        # Debug: Ausgabe der vollständigen Antwort von OpenAI
        print("Antwort von OpenAI:", response)

        if not response or 'choices' not in response or len(response['choices']) == 0:
            raise HTTPException(status_code=500, detail="Keine Antwort von OpenAI erhalten")

        ai_response = response['choices'][0]['message'].get('content')
        if not ai_response:
            raise HTTPException(status_code=500, detail="Die Antwort von OpenAI ist leer")

        # Verarbeite die Antwort von OpenAI
        ai_user_data = extract_data_from_ai_response(ai_response)

        # Debugging: Ausgabe der extrahierten Daten
        print("Extrahierte Daten von OpenAI:", ai_user_data)

        # Überprüfe, ob alle erforderlichen Daten extrahiert wurden
        required_keys = ['inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value']
        missing_keys = [key for key in required_keys if key not in ai_user_data or not ai_user_data[key]]
        if missing_keys:
            questions = request_additional_information(missing_keys)
            return templates.TemplateResponse("missing_data.html", {"request": request, "questions": questions,
                                                                    "provided_data": json.dumps(ai_user_data)})

        # Formatieren des Datums
        try:
            formatted_date = parse_date(ai_user_data['inspection date'])
            ai_user_data['inspection date'] = formatted_date
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Rückgabe der extrahierten Daten und Weiterleitung zur Formularanzeige
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
        missing_data_4: Optional[str] = Form(None)
):
    try:
        # Debugging-Ausgabe, um zu prüfen, welche Daten empfangen werden
        print("Bereitgestellte Daten (raw):", provided_data)
        print("Fehlende Daten:", missing_data_1, missing_data_2, missing_data_3, missing_data_4)

        # Versuche, die bereitgestellten Daten als JSON zu dekodieren
        try:
            provided_data = json.loads(provided_data)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Fehler beim Dekodieren der bereitgestellten Daten: {str(e)}")

        # Extrahiere die fehlenden Schlüssel
        required_keys = ['inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value']
        missing_keys = [key for key in required_keys if key not in provided_data or not provided_data[key]]

        # Füge die fehlenden Daten hinzu
        missing_data = [
            missing_data_1,
            missing_data_2,
            missing_data_3,
            missing_data_4
        ]

        for key, value in zip(missing_keys, missing_data):
            if value:
                provided_data[key] = value.strip()

        # Entferne Sternchen (**) und überflüssige Leerzeichen aus den Werten
        for key in provided_data:
            if isinstance(provided_data[key], str):
                provided_data[key] = provided_data[key].replace('**', '').strip()

        # Prüfe, ob alle erforderlichen Daten vorhanden sind
        for key in required_keys:
            if key not in provided_data or not provided_data[key]:
                raise HTTPException(status_code=400, detail=f"Fehlender Wert für {key}")

        # Formatieren des Datums
        try:
            formatted_date = parse_date(provided_data['inspection date'])
            provided_data['inspection date'] = formatted_date
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Debugging: Ausgabe der kombinierten und bereinigten Daten
        print("Kombinierte und bereinigte Daten:", provided_data)

        return templates.TemplateResponse("indexAI.html", {"request": request, "data": provided_data})

    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Anfrage an OpenAI: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Verarbeiten der Daten: {str(e)}")
