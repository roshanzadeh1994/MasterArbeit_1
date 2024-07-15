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
import subprocess
import tempfile

locale.setlocale(locale.LC_TIME, "de_DE")

router = APIRouter(tags=["router_AI"])
templates = Jinja2Templates(directory="templates")

# OpenAI API-Key
openai.api_key = 'sk-proj-uSLL0VokwK420NRtURgqT3BlbkFJK21oMFYqydJI9jD4qpzR'


class UserText(BaseModel):
    userText: str


# --------------------------------------*************--------------------------------


@router.get("/signupAI/", response_class=HTMLResponse)
async def signup(request: Request):
    return templates.TemplateResponse("signupAI.html", {"request": request})


@router.post("/signupAI/submit", response_class=HTMLResponse)
async def process_signup(userText: str = Form(...), db: Session = Depends(get_db)):
    try:
        # Anfrage an OpenAI stellen
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                {"role": "user",
                 "content": f"Extrahiere den Benutzernamen, die E-Mail und das Passwort aus diesem Text: {userText}"}
            ],
            max_tokens=100
        )

        # Verarbeite die Antwort von OpenAI
        data = response['choices'][0]['message']['content'].strip().split('\n')
        ai_user_data = {}
        for item in data:
            key_value = item.split(':')
            if len(key_value) == 2:
                key = key_value[0].strip().lower()
                value = key_value[1].strip()

                if 'user' in key or 'username' in key or 'User' in key or 'Name' in key or 'name' in key or 'Benutzer' in key or 'Benutzername' in key:
                    key = 'benutzername'
                if 'pass' in key or 'password' in key or 'passwort' in key or 'Pass' in key or 'secret' in key or 'pin' in key:
                    key = 'passwort'
                if 'email' in key or 'Email' in key or 'E-mail' in key or 'mail' in key or 'Mail' in key or 'e-mail' in key:
                    key = 'e-mail'

                ai_user_data[key] = value

        # Überprüfe, ob alle erforderlichen Daten extrahiert wurden
        required_keys = ['benutzername', 'passwort', 'e-mail']  # Schlüsselnamen anpassen
        for key in required_keys:
            if key not in ai_user_data:
                raise HTTPException(status_code=400,
                                    detail=f"Schlüssel '{key}' wurde nicht in den extrahierten Daten gefunden")

        # Überprüfe, ob der Benutzer bereits existiert
        existing_user = db.query(models.DbUser).filter(models.DbUser.username == ai_user_data['benutzername']).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Benutzername bereits registriert")

        # Benutzer erstellen, wenn alles in Ordnung ist
        user = create_user(db, schemas.UserBase(username=ai_user_data['benutzername'], email=ai_user_data['e-mail'],
                                                password=ai_user_data['passwort']))

        # Rückgabe der extrahierten Daten als HTML-Antwort
        return HTMLResponse(content=f"""
                <h1>Extrahierte Daten:</h1>
                <p>Benutzername: {ai_user_data['benutzername']}</p>
                <p>E-Mail: {ai_user_data['e-mail']}</p>
                <p>Passwort: {ai_user_data['passwort']}</p>
                <button onclick="window.location.href='/'">🏠 Home</button>
            """)

    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Anfrage an OpenAI: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Verarbeiten der OpenAI-Antwort: {str(e)}")


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
                {"role": "user", "content": f"Extrahiere die relevanten Daten aus diesem Text: {userText}"}
            ],
            max_tokens=100
        )

        # Verarbeite die Antwort von OpenAI
        data = response['choices'][0]['message']['content'].strip().split('\n')
        ai_user_data = {}
        for item in data:
            key_value = item.split(':')
            if len(key_value) == 2:
                key = key_value[0].strip().lower().replace('-', '').strip()
                value = key_value[1].strip()
                # Mapping der Schlüssel von OpenAI auf die erwarteten Schlüssel
                if 'ort' in key or 'location' in key or 'Standort' in key or 'place' in key or 'Location' in key or 'city' in key or 'Stadt' in key or 'stadt' in key:
                    key = 'inspection location'
                if 'schiffsname' in key or 'schiffname' in key or 'ship' in key or 'Schiff' in key or 'name of ship' in key or 'name des Schiffs' in key or 'name des schiffes' in key or 'schiffsname' in key or 'schiffsname' in key or 'name des schiffs' in key:
                    key = 'ship name'
                if 'inspektionsdatum' in key or 'Datum' in key or 'date' in key or 'datum' in key:
                    key = 'inspection date'
                if 'inspektionsdetails' in key or 'details' in key or 'detail' in key or 'Beschreibung' in key or 'Eklärung' in key:
                    key = 'inspection details'
                if 'numerischer wert' in key or 'Nummer' in key or 'nummer' in key or 'number' in key or 'numerical' in key or 'numerische' in key or 'numerisch' in key or '':
                    key = 'numerical value'
                ai_user_data[key] = value

        # Debugging: Ausgabe der extrahierten Daten
        print("Extrahierte Daten von OpenAI:", ai_user_data)

        # Überprüfe, ob alle erforderlichen Daten extrahiert wurden
        required_keys = ['inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value']
        missing_keys = [key for key in required_keys if key not in ai_user_data]
        if missing_keys:
            raise HTTPException(status_code=400,
                                detail=f"Schlüssel {missing_keys} wurden nicht in den extrahierten Daten gefunden *** geschrieben Daten sind :(( {ai_user_data} )) ***")

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


@router.post("/process_voice", response_class=HTMLResponse)
async def process_voice(request: Request, audioFile: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        # Temporäre Datei für die Audiodatei erstellen
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
            temp_audio_file.write(await audioFile.read())
            temp_audio_file_path = temp_audio_file.name

        # Audiodatei in Text konvertieren (mit OpenAI oder einem anderen Speech-to-Text-Service)
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
                {"role": "user", "content": f"Extrahiere die relevanten Daten aus diesem Text: {userText}"}
            ],
            max_tokens=100
        )

        # Verarbeite die Antwort von OpenAI
        data = response['choices'][0]['message']['content'].strip().split('\n')
        ai_user_data = {}
        for item in data:
            key_value = item.split(':')
            if len(key_value) == 2:
                key = key_value[0].strip().lower().replace('-', '').strip()
                value = key_value[1].strip()
                # Mapping der Schlüssel von OpenAI auf die erwarteten Schlüssel
                if 'ort' in key or 'location' in key or 'Standort' in key or 'place' in key or 'Location' in key or 'city' in key or 'Stadt' in key or 'stadt' in key:
                    key = 'inspection location'
                if 'schiffsname' in key or 'schiffname' in key or 'ship' in key or 'Schiff' in key or 'name of ship' in key or 'name des Schiffs' in key or 'name des schiffes' in key or 'schiffsname' in key or 'schiffsname' in key or 'name des schiffs' in key:
                    key = 'ship name'
                if 'inspektionsdatum' in key or 'Datum' in key or 'date' in key or 'datum' in key:
                    key = 'inspection date'
                if 'inspektionsdetails' in key or 'details' in key or 'detail' in key or 'Beschreibung' in key or 'Eklärung' in key:
                    key = 'inspection details'
                if 'numerischer wert' in key or 'Nummer' in key or 'nummer' in key or 'number' in key or 'numerical' in key or 'numerische' in key or 'numerisch' in key:
                    key = 'numerical value'
                ai_user_data[key] = value

        # Debugging: Ausgabe der extrahierten Daten
        print("Extrahierte Daten von OpenAI:", ai_user_data)

        # Überprüfe, ob alle erforderlichen Daten extrahiert wurden
        required_keys = ['inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value']
        missing_keys = [key for key in required_keys if key not in ai_user_data]
        if missing_keys:
            raise HTTPException(status_code=400,
                                detail=f"Schlüssel {missing_keys} wurden nicht in den extrahierten Daten gefunden *** geschrieben Daten sind :(( {ai_user_data} )) ***")

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
