from fastapi.testclient import TestClient
import sys
import os

# Den absoluten Pfad zum Projektverzeichnis hinzufügen, damit `main` gefunden wird
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app

# Erstelle einen Test-Client für deine FastAPI-Anwendung
client = TestClient(app)


def test_create_token():
    """
    Testet die Erstellung eines Tokens.
    """
    # Simulation eines Benutzers
    response = client.post("/token", data={"username": "testuser", "password": "testpassword"})

    # Überprüfe, ob der Statuscode 200 ist (d.h., die Anfrage war erfolgreich)
    assert response.status_code == 200

    # Überprüfe, ob der Zugriffstoken im Antwortkörper enthalten ist
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data["type_token"] == "bearer"


def test_create_token_invalid_credentials():
    """
    Testet die Erstellung eines Tokens mit falschen Anmeldedaten.
    """
    response = client.post("/token", data={"username": "wronguser", "password": "wrongpassword"})

    # Überprüfe, ob der Statuscode 404 ist (d.h., die Anfrage schlägt fehl wegen falscher Anmeldedaten)
    assert response.status_code == 404
