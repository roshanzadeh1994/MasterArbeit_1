import pandas as pd
from db.models import ShipInspection
from db.db_ship import create_ship_inspection
import schemas
import tempfile
from fastapi import APIRouter, status, Depends, UploadFile, File
from sqlalchemy.orm import Session
from auth.oauth2 import get_current_user
from auth.authentication import get_token
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from db.database import Base, get_db
from fastapi import Form
from fastapi import Depends, HTTPException

templates = Jinja2Templates(directory="templates")

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


async def check_authentication(user: schemas.UserAuth = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="You must be logged in to access this page")


@router.post("/login/", response_class=RedirectResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    form = OAuth2PasswordRequestForm(username=username, password=password)
    token_data = get_token(form, db)
    # Nach erfolgreichem Login auf die Indexseite umleiten
    return RedirectResponse(url="/formular")


@router.get("/formular", response_class=HTMLResponse, dependencies=[Depends(check_authentication)])
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/formular", response_class=HTMLResponse)
async def process_form(request: Request, username: str = Form(...), password: str = Form(...)):
    # Hier können Sie die Formulardaten verarbeiten, z.B. Authentifizierung, Überprüfung usw.
    # Nach der Verarbeitung können Sie den Benutzer an eine andere Seite weiterleiten oder eine Antwort zurückgeben
    return templates.TemplateResponse("index.html", {"request": request})


# @router.post("/submit/")
# async def submit_ship_inspection(request: Request,
#                                  db: Session = Depends(get_db),
#                                  current_user: schemas.UserAuth = Depends(get_current_user)):


@router.post("/submit/")
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
