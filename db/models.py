# Importieren Sie benötigte Module
from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime
from db.database import Base
from sqlalchemy.orm import relationship


# Definieren Sie Ihre Datenbankmodelle für die Schiffsinspektion
class ShipInspection(Base):
    __tablename__ = "ship_inspection"

    id = Column(Integer, index=True, primary_key=True)
    inspection_date = Column(DateTime, default=datetime.utcnow)
    inspection_location = Column(String)
    ship_name = Column(String)
    inspection_details = Column(String)


# Funktion zum Hinzufügen einer Schiffsinspektion in die Datenbank
def create_ship_inspection(db, inspection_data):
    inspection = ShipInspection(**inspection_data)
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


# Funktion zum Abrufen aller Schiffsinspektionen aus der Datenbank
def get_all_ship_inspections(db):
    return db.query(ShipInspection).all()


# Funktion zum Abrufen einer einzelnen Schiffsinspektion anhand der ID
def get_ship_inspection_by_id(db, inspection_id):
    return db.query(ShipInspection).filter(ShipInspection.id == inspection_id).first()
