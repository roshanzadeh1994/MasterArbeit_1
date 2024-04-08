from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base,get_db
from db.models import create_ship_inspection
from sqlalchemy.orm import Session

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Create engine and session
engine = create_engine("sqlite:///projTeste1.db", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine)


# Create Jinja2Templates instance
templates = Jinja2Templates(directory="templates")


class ShipInspectionInput(BaseModel):
    inspection_location: str
    ship_name: str
    inspection_details: str
    numerical_value: int


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/submit/")
async def submit_ship_inspection(request: Request):
    data = await request.form()
    inspection_location = data.get("inspection_location")
    ship_name = data.get("ship_name")
    inspection_details = data.get("inspection_details")
    numerical_value = int(data.get("numerical_value"))

    # Verarbeiten Sie die Daten hier weiter...

    return {"status": "success"}


@app.get("/download/")
async def download_ship_inspections():
    # Hier könnten Sie Ihre Funktionen zum Abrufen der gespeicherten Schiffsinspektionen aus der Datenbank aufrufen
    # Hier nur Beispielcode
    data = {
        "Inspection Location": ["Location 1", "Location 2"],
        "Ship Name": ["Ship A", "Ship B"],
        "Inspection Details": ["Details 1", "Details 2"],
        "Numerical Value": [10.5, 20.3]
    }
    df = pd.DataFrame(data)
    filename = "ship_inspections.xlsx"
    df.to_excel(filename, index=False)
    return FileResponse(filename, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
