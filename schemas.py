from pydantic import BaseModel


class ShipInspectionInput(BaseModel):
    inspection_location: str
    ship_name: str
    inspection_details: str
    numerical_value: int
