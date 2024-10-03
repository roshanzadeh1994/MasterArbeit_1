from sqlalchemy import Column, String, Integer, ForeignKey, Date  # Import von SQLAlchemy-Spaltentypen und ForeignKey
from db.database import Base  # Import der Basisklasse für ORM-Modelle
from sqlalchemy.orm import relationship  # Import für die Verwaltung von Beziehungen zwischen Tabellen


# Definition des Benutzermodells in der Datenbank
class DbUser(Base):
    """
    Repräsentiert einen Benutzer in der Datenbank.

    Attribute:
    - id (Integer): Primärschlüssel des Benutzers.
    - username (String): Der Benutzername.
    - password (String): Das gehashte Passwort des Benutzers.
    - email (String): Die E-Mail-Adresse des Benutzers.
    - items (relationship): Beziehung zu den Schiffsinspektionen, die der Benutzer erstellt hat.
    """
    __tablename__ = "user"  # Der Name der Tabelle in der Datenbank

    id = Column(Integer, index=True, primary_key=True)  # Primärschlüssel und indexierte Spalte
    username = Column(String)  # Benutzername des Benutzers
    password = Column(String)  # Passwort des Benutzers (wird gehasht gespeichert)
    email = Column(String)  # E-Mail-Adresse des Benutzers
    items = relationship("ShipInspection",
                         back_populates="user")  # Beziehung zu ShipInspection (Ein Benutzer hat mehrere Inspektionen)


# Definition des Schiffsinspektionsmodells in der Datenbank
class ShipInspection(Base):
    """
    Repräsentiert eine Schiffsinspektion in der Datenbank.

    Attribute:
    - id (Integer): Primärschlüssel der Inspektion.
    - inspection_location (String): Ort der Inspektion.
    - ship_name (String): Name des inspizierten Schiffs.
    - inspection_date (Date): Datum der Inspektion.
    - inspection_details (String): Detaillierte Informationen zur Inspektion.
    - numerical_value (Integer): Ein numerischer Wert zur Bewertung der Inspektion.
    - user_id (Integer): Fremdschlüssel, der den Benutzer identifiziert, der die Inspektion durchgeführt hat.
    - user (relationship): Beziehung zum Benutzer, der die Inspektion erstellt hat.
    """
    __tablename__ = "ship_inspection"  # Der Name der Tabelle in der Datenbank

    id = Column(Integer, index=True, primary_key=True)  # Primärschlüssel und indexierte Spalte
    inspection_location = Column(String)  # Ort der Schiffsinspektion
    ship_name = Column(String)  # Name des inspizierten Schiffs
    inspection_date = Column(Date)  # Datum der Inspektion
    inspection_details = Column(String)  # Detaillierte Beschreibung der Inspektion
    numerical_value = Column(Integer)  # Ein numerischer Wert für die Bewertung der Inspektion
    user_id = Column(Integer, ForeignKey('user.id'))  # Fremdschlüssel, der auf den Benutzer verweist (user.id)

    # Beziehung zum Benutzermodell: Eine Inspektion gehört zu einem Benutzer
    user = relationship("DbUser", back_populates="items")
