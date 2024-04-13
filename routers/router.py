import pandas as pd
from db.models import create_ship_inspection, ShipInspection
import schemas
import tempfile
from fastapi import APIRouter, status, Depends, UploadFile, File
from sqlalchemy.orm import Session
from db.database import get_db
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from auth.oauth2 import get_current_user


router = APIRouter()


@router.post("/submit/")
async def submit_ship_inspection(request: Request, db: Session = Depends(get_db)): #, current_user: schemas.UserAuth = Depends(get_current_user)
    form_data = await request.form()
    inspection_location = form_data.get("inspection_location")
    ship_name = form_data.get("ship_name")
    inspection_details = form_data.get("inspection_details")
    numerical_value = int(form_data.get("numerical_value"))

    ship_inspection = schemas.ShipInspectionInput(
        inspection_location=inspection_location,
        ship_name=ship_name,
        inspection_details=inspection_details,
        numerical_value=numerical_value
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
            "Numerical Value": [inspection.numerical_value for inspection in inspections]
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
