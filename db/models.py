from sqlalchemy import Column, String, Integer, ForeignKey
from db.database import Base
from sqlalchemy.orm import relationship


class DbUser(Base):
    __tablename__ = "user"

    id = Column(Integer, index=True, primary_key=True)
    username = Column(String)
    password = Column(String)
    email = Column(String)
    items = relationship("ShipInspection", back_populates="user")


# Definieren Sie Ihre Datenbankmodelle für die Schiffsinspektion
class ShipInspection(Base):
    __tablename__ = "ship_inspection"

    id = Column(Integer, index=True, primary_key=True)
    inspection_location = Column(String)
    ship_name = Column(String)
    inspection_details = Column(String)
    numerical_value = Column(Integer)
    user_id = Column(Integer, ForeignKey('user.id'))
    # Beziehung zu Benutzer
    user = relationship("DbUser", back_populates="items")
