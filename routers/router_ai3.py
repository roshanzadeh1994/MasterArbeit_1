from fastapi import APIRouter, Form, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import openai
from pydantic import BaseModel
import schemas
from db import models
from db.database import get_db
from db.db_user import create_user, get_user_by_username_password
from datetime import datetime
import locale
import os
import tempfile
from fastapi.responses import RedirectResponse
from routers.router import homepage

locale.setlocale(locale.LC_TIME, "de_DE")

router = APIRouter(tags=["router_AI"])
templates = Jinja2Templates(directory="templates")

# OpenAI API-Key
openai.api_key = 'sk-proj-uSLL0VokwK420NRtURgqT3BlbkFJK21oMFYqydJI9jD4qpzR'


class UserText(BaseModel):
    userText: str


# -----------------*************************---------------------*************--------------------------------

def parse_date(date_str):
    # Konvertiert ein Datum im natürlichen Sprachformat in das Format 'dd.mm.yyyy'.
    try:
        # Versuche das Datum im Format 'dd.mm.yyyy' zu parsen
        return datetime.strptime(date_str, '%d.%m.%Y').strftime('%Y-%m-%d')
    except ValueError:
        try:
            # Versuche das Datum im natürlichen Sprachformat zu parsen
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
            # Mapping der Schlüssel von OpenAI auf die erwarteten Schlüssel
            if 'ort' in key or 'location' in key or 'standort' in key or 'place' in key or 'location' in key or 'city' in key or 'Stadt' in key:
                key = 'inspection location'
            if 'schiffsname' in key or 'schiffname' in key or 'ship' in key or 'schiff' in key or 'name of ship' in key or 'name des schiffs' in key:
                key = 'ship name'
            if 'inspektionsdatum' in key or 'datum' in key or 'date' in key:
                key = 'inspection date'
            if 'inspektionsdetails' in key or 'details' in key or 'beschreibung' in key or 'erklärung' in key:
                key = 'inspection details'
            if 'numerischer wert' in key or 'nummer' in key or 'number' in key or 'numerical' in key or 'numerische' in key or 'numerisch' in key:
                key = 'numerical value'
            ai_user_data[key] = value
    return ai_user_data


@router.get("/text_input", response_class=HTMLResponse)
async def text_input(request: Request):
    return templates.TemplateResponse("Text-input.html", {"request": request})


@router.post("/process_text", response_class=HTMLResponse)
async def process_text(request: Request, userText: str = Form(...), db: Session = Depends(get_db)):
    try:
        # Anfrage an OpenAI stellen
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                {"role": "user", "content": f"Extrahiere die relevanten Daten(location, ship name, date, details, "
                                            f"numerical value) aus diesem Text: {userText}"}
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
        missing_keys = [key for key in required_keys if key not in ai_user_data]
        if missing_keys:
            return templates.TemplateResponse("missing_data.html", {"request": request, "missing_keys": missing_keys, "provided_data": ai_user_data})

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


@router.get("/process_voice", response_class=HTMLResponse)
async def process_voice(request: Request):
    return templates.TemplateResponse("Text-input.html", {"request": request})


@router.post("/process_voice", response_class=HTMLResponse)
async def process_voice(request: Request, audioFile: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        # Temporäre Datei für die Audiodatei erstellen
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
            temp_audio_file.write(await audioFile.read())
            temp_audio_file_path = temp_audio_file.name

        # Audiodatei in Text konvertieren (mit whisper-1 Speech-to-Text-Service)
        with open(temp_audio_file_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file
            )

        userText = response['text']

        # Löschen der temporären Audiodatei
        os.remove(temp_audio_file_path)

        # Weiterverarbeitung des Textes wie in der process_text-Funktion
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                {"role": "user", "content": f"Extrahiere die relevanten Daten(location, ship name, date, details, "
                                            f"numerical value) aus diesem Text: {userText}"}
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
        missing_keys = [key for key in required_keys if key not in ai_user_data]
        if missing_keys:
            return templates.TemplateResponse("missing_data.html", {"request": request, "missing_keys": missing_keys, "provided_data": ai_user_data})

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
