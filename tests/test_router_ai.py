from fastapi.testclient import TestClient
from routers import router_ai
from main import app
from unittest.mock import patch

client = TestClient(app)

# Beispielantwort von OpenAI simulieren
mock_openai_response = {
    "choices": [
        {
            "message": {
                "content": "Inspection Location: Berlin\nShip Name: Titanic\nInspection Date: 2023-10-01\nInspection Details: Routine check\nNumerical Value: 42"
            }
        }
    ]
}

# Test für den Endpunkt der HTML-Rückgabe
@patch("routers.router_ai.openai.ChatCompletion.create")
def test_process_text(mock_openai_create):
    # Simuliere die Antwort von OpenAI
    mock_openai_create.return_value = mock_openai_response

    # Sende eine POST-Anfrage an die Route
    response = client.post("/process_text", data={"userText": "This is a test input"})

    # Überprüfen, ob der Statuscode 200 ist (erfolgreich)
    assert response.status_code == 200

    # Überprüfe, ob der HTML-Inhalt relevante Daten enthält
    html_content = response.text

    # Sicherstellen, dass der HTML-Inhalt die erwarteten Werte enthält
    assert '<input type="text" id="inspection_location" name="inspection_location" value="Berlin"' in html_content
    assert '<input type="text" id="ship_name" name="ship_name" value="Titanic"' in html_content
    assert '<input type="date" id="inspection_date" name="inspection_date" value="2023-10-01"' in html_content
    assert '<textarea id="inspection_details" name="inspection_details" rows="5" required>Routine check</textarea>' in html_content

    # Flexible Überprüfung der numerischen Eingabe (entweder mit oder ohne Dezimalstelle)
    assert '<input type="number" id="numerical_value" name="numerical_value" min="0" step="1" value="42"' in html_content or \
           '<input type="number" id="numerical_value" name="numerical_value" min="0" step="1" value="42.0"' in html_content
