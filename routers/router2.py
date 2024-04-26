import pandas as pd
from jose import jwt, JWTError

from db.models import ShipInspection
from db.db_ship import create_ship_inspection
import schemas
import tempfile
from fastapi.responses import HTMLResponse, FileResponse
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security.oauth2 import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm.session import Session
from auth.oauth2 import get_current_user
from db import models
from db.database import get_db
from db.hash import Hash
from auth import oauth2
from db.models import DbUser
from schemas import UserAuth, UserBase
from fastapi import FastAPI, Request
from db.db_user import create_user
from fastapi.responses import RedirectResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates")

"""
@router.post("/login", response_class=RedirectResponse)
def login(request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.DbUser).filter(models.DbUser.username == request.username).first()
    if not user or not Hash.verify(user.password, request.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    access_token = oauth2.create_access_token(data={"sub": request.username})
    return RedirectResponse(url="/login/formular")


@router.post("/login/formular", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

"""

from typing import Optional
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from fastapi import Cookie


@router.post("/login", response_class=RedirectResponse)
def login(request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.DbUser).filter(models.DbUser.username == request.username).first()
    if not user or not Hash.verify(user.password, request.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    access_token = oauth2.create_access_token(data={"sub": request.username})
    # Save user information in cookie
    response = RedirectResponse(url="/login/formular")
    response.set_cookie(key="user_id", value=str(user.id))
    response.set_cookie(key="username", value=user.username)
    return response




@router.get("/login/formular", response_class=HTMLResponse)
async def index(request: Request, user_id: Optional[str] = Cookie(None), username: Optional[str] = Cookie(None)):
    # Retrieve user information from cookies
    if not user_id or not username:
        # Handle case when user information is not available
        return RedirectResponse(url="/login")
    # Use user information in your HTML template
    return templates.TemplateResponse("index.html", {"request": request, "user_id": user_id, "username": username})


@router.post("/login/formular", response_class=HTMLResponse)
async def process_login_form(request: Request, db: Session = Depends(get_db)):
    # Hier den Login-Logik durchführen, einschließlich der Überprüfung von Benutzername und Passwort
    # Nach erfolgreicher Überprüfung weiterleiten oder Fehler behandeln
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/login/formular/submit/")
async def submit_ship_inspection(request: Request, db: Session = Depends(get_db),
                                 user_id: Optional[str] = Cookie(None)):
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")

    form_data = await request.form()
    inspection_location = form_data.get("inspection_location")
    ship_name = form_data.get("ship_name")
    inspection_details = form_data.get("inspection_details")
    numerical_value = int(form_data.get("numerical_value"))

    ship_inspection = schemas.ShipInspectionInput(
        inspection_location=inspection_location,
        ship_name=ship_name,
        inspection_details=inspection_details,
        numerical_value=numerical_value,
        user_id=int(user_id),  # Convert user_id to int
    )

    return create_ship_inspection(db, ship_inspection.dict())


@router.get("/", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/signup", response_class=HTMLResponse)
async def signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@router.post("/signup", response_model=UserBase)
def create_new_user(user: UserBase, db: Session = Depends(get_db)):
    new_user = create_user(db=db, request=UserBase(username=user.username, email=user.email,
                                                   password=Hash.bcrypt(user.password)))
    return new_user


"""
@router.post("/login/formular/submit/")
async def submit_ship_inspection(request: Request, db: Session = Depends(
    get_db)):  # , current_user: schemas.UserAuth = Depends(get_current_user)
    form_data = await request.form()
    inspection_location = form_data.get("inspection_location")
    ship_name = form_data.get("ship_name")
    inspection_details = form_data.get("inspection_details")
    numerical_value = int(form_data.get("numerical_value"))
    user_id = int(form_data.get("user_id", 0))  # Default to 0 if user_id is not provided

    ship_inspection = schemas.ShipInspectionInput(
        inspection_location=inspection_location,
        ship_name=ship_name,
        inspection_details=inspection_details,
        numerical_value=numerical_value,
        user_id=user_id,

    )

    return create_ship_inspection(db, ship_inspection.dict())

"""


@router.get("/download/")
async def download_ship_inspections(db: Session = Depends(get_db)):
    try:
        inspections = db.query(ShipInspection).all()

        if not inspections:
            raise HTTPException(status_code=404, detail="No ship inspections found")

        inspection_data = {
            "Inspection Location": [inspection.inspection_location for inspection in inspections],
            "Ship Name": [inspection.ship_name for inspection in inspections],
            "Inspection Details": [inspection.inspection_details for inspection in inspections],
            "Numerical Value": [inspection.numerical_value for inspection in inspections],
            "User_id": [inspection.user_id for inspection in inspections]

        }

        df = pd.DataFrame(inspection_data)

        # Erstelle eine temporäre Datei
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            filename = tmp_file.name

            # Schreibe den DataFrame in die temporäre Datei
            df.to_excel(tmp_file, index=False)

        # Gebe die temporäre Datei zurück
        return FileResponse(filename, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
