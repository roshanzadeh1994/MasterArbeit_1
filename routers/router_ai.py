from fastapi import APIRouter, Form, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import openai
from pydantic import BaseModel
import schemas
from db import models
from db.database import get_db
from db.db_user import create_user, get_user_by_username_password


router = APIRouter(tags=["router_AI"])
templates = Jinja2Templates(directory="templates")

# OpenAI API-Key (ersetze durch deinen eigenen API-Key)
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
                ai_user_data[key] = value

        # Überprüfe, ob alle erforderlichen Daten extrahiert wurden
        required_keys = ['benutzername', 'passwort']  # Schlüsselnamen anpassen
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


# --------------------------------------*************--------------------------------

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
                key = key_value[0].strip().lower()
                value = key_value[1].strip()
                ai_user_data[key] = value

        # Debugging: Ausgabe der extrahierten Daten
        print("Extrahierte Daten von OpenAI:", ai_user_data)

        # Überprüfe, ob alle erforderlichen Daten extrahiert wurden
        required_keys = ['inspection location', 'ship name', 'inspection date', 'inspection details', 'numerical value']
        for key in required_keys:
            if key not in ai_user_data:
                raise HTTPException(status_code=400,
                                    detail=f"Schlüssel '{key}' wurde nicht in den extrahierten Daten gefunden")

        # Rückgabe der extrahierten Daten und Weiterleitung zur Formularanzeige
        return templates.TemplateResponse("auto_filled_form.html", {"request": request, "data": ai_user_data})

    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Anfrage an OpenAI: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Verarbeiten der OpenAI-Antwort: {str(e)}")
