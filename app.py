# -*- coding: utf-8 -*-
"""
Created on Tue May  5 14:25:16 2026

@author: pcdan
"""


#CODE POUR SERVEUR WEB 

from flask import Flask, request, jsonify, render_template_string
import requests
from datetime import datetime

app = Flask(__name__)

# ---------------------------
# Configuration serveur FHIR local
# ---------------------------
URL_PATIENT = "http://localhost:8080/fhir/Patient"
URL_OBS = "http://localhost:8080/fhir/Observation"

# ---------------------------
# HTML commun avec toutes les étapes
# ---------------------------
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>TP FHIR Interface</title>
    <style>
        body { font-family: Arial; margin: 30px; background: #f9f9f9; }
        h1 { color: #2c3e50; }
        h2 { color: #34495e; margin-top: 40px; }
        form { background: #ecf0f1; padding: 20px; margin-bottom: 20px; border-radius: 10px; }
        input, select { padding: 5px; margin: 5px 0; width: 100%; }
        button { padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #2980b9; }
        .result { background: #dfe6e9; padding: 10px; border-radius: 5px; margin-top: 10px; white-space: pre-wrap; }
        p { font-size: 14px; }
    </style>
</head>
<body>
    <h1>TP FHIR : Gestion Patient & Observation</h1>
    
    <h2>Étape 1 : Comprendre la structure d’une ressource</h2>
    <p>Consultez la documentation FHIR pour <b>Patient</b> et <b>Observation</b>.<br>
    Observation fréquence cardiaque minimale : status, category (vital-signs), code LOINC (8867-4), subject (Patient), effectiveDateTime, valueQuantity.</p>

    <h2>Étape 2 : Création d’un patient</h2>
    <form method="post" action="/create_patient">
        Nom de famille: <input name="family" required><br>
        Prénom: <input name="given" required><br>
        Genre:
        <select name="gender">
            <option value="male">male</option>
            <option value="female">female</option>
            <option value="other">other</option>
            <option value="unknown">unknown</option>
        </select><br>
        Date de naissance: <input type="date" name="birthDate" required><br>
        <button type="submit">Créer Patient</button>
    </form>

    <h2>Étape 3 : Création d’une observation</h2>
    <form method="post" action="/create_observation">
        Patient ID: <input name="patient_id" required><br>
        Valeur (bpm): <input type="number" name="value" value="72" required><br>
        Date et heure (optionnel): <input type="datetime-local" name="datetime"><br>
        <button type="submit">Créer Observation</button>
    </form>

    <h2>Étape 3b : Mise à jour d’une observation</h2>
    <form method="post" action="/update_observation">
        Observation ID: <input name="obs_id" required><br>
        Nouvelle valeur (bpm): <input type="number" name="value" required><br>
        <button type="submit">Mettre à jour Observation</button>
    </form>

    <h2>Étape 4 : Lire / Supprimer une observation</h2>
    <form method="post" action="/manage_observation">
        Observation ID: <input name="obs_id" required><br>
        Action:
        <select name="action">
            <option value="get">Lire (GET)</option>
            <option value="delete">Supprimer (DELETE)</option>
        </select><br>
        <button type="submit">Exécuter</button>
    </form>

    <h2>Étape 5 : Gestion des erreurs</h2>
    <form method="post" action="/test_error">
        <button type="submit">Envoyer JSON incomplet pour erreur 400</button>
    </form>

    {% if result %}
    <h2>Résultat :</h2>
    <div class="result">{{ result }}</div>
    {% endif %}
</body>
</html>
"""

# ---------------------------
# Routes Flask
# ---------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)

# Étape 2 : créer patient
@app.route("/create_patient", methods=["POST"])
def create_patient():
    data = request.form
    patient = {
        "resourceType": "Patient",
        "name": [{"family": data.get("family"), "given": [data.get("given")]}],
        "gender": data.get("gender"),
        "birthDate": data.get("birthDate")
    }
    try:
        resp = requests.post(URL_PATIENT, json=patient)
        result = resp.json() if resp.status_code == 201 else f"Erreur {resp.status_code}: {resp.text}"
    except Exception as e:
        result = str(e)
    return render_template_string(HTML_PAGE, result=result)

# Étape 3 : créer observation
@app.route("/create_observation", methods=["POST"])
def create_observation():
    data = request.form
    patient_id = data.get("patient_id")
    if not patient_id:
        return render_template_string(HTML_PAGE, result="Patient ID requis")
    dt_input = data.get("datetime")
    dt = datetime.fromisoformat(dt_input) if dt_input else datetime.now()
    observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category","code": "vital-signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org","code": "8867-4","display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": dt.isoformat(),
        "valueQuantity": {"value": int(data.get("value", 72)), "unit": "beats/minute","system": "http://unitsofmeasure.org","code": "/min"}
    }
    try:
        resp = requests.post(URL_OBS, json=observation)
        result = resp.json() if resp.status_code == 201 else f"Erreur {resp.status_code}: {resp.text}"
    except Exception as e:
        result = str(e)
    return render_template_string(HTML_PAGE, result=result)

# Étape 3b : mise à jour observation
@app.route("/update_observation", methods=["POST"])
def update_observation():
    data = request.form
    obs_id = data.get("obs_id")
    new_value = data.get("value")
    if not obs_id or not new_value:
        return render_template_string(HTML_PAGE, result="obs_id et value requis")
    try:
        resp_get = requests.get(f"{URL_OBS}/{obs_id}")
        obs_data = resp_get.json()
        obs_data["valueQuantity"]["value"] = int(new_value)
        resp_put = requests.put(f"{URL_OBS}/{obs_id}", json=obs_data)
        result = resp_put.json()
    except Exception as e:
        result = str(e)
    return render_template_string(HTML_PAGE, result=result)

# Étape 4 : lire / supprimer observation
@app.route("/manage_observation", methods=["POST"])
def manage_observation():
    data = request.form
    obs_id = data.get("obs_id")
    action = data.get("action")
    result = ""
    try:
        url = f"{URL_OBS}/{obs_id}"
        if action == "get":
            resp = requests.get(url)
            result = resp.json()
        elif action == "delete":
            resp = requests.delete(url)
            result = {"status_code": resp.status_code, "message": "Observation supprimée"}
    except Exception as e:
        result = str(e)
    return render_template_string(HTML_PAGE, result=result)

# Étape 5 : gestion des erreurs
@app.route("/test_error", methods=["POST"])
def test_error():
    bad_patient = {"resourceType": "InvalidType", "name": [{"family": "Test"}]}
    try:
        resp = requests.post(URL_PATIENT, json=bad_patient)
        result = {"status_code": resp.status_code, "response": resp.text}
    except Exception as e:
        result = str(e)
    return render_template_string(HTML_PAGE, result=result)

# ---------------------------
# Lancer Flask
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)