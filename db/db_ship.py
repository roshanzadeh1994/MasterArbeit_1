from db.models import ShipInspection
from sqlalchemy.orm.session import Session


# Funktion zum Hinzufügen einer Schiffsinspektion in die Datenbank
def create_ship_inspection(db: Session, inspection_data):
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

