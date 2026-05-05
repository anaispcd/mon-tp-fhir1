# -*- coding: utf-8 -*-
"""
Created on Tue May  5 14:25:16 2026

@author: pcdan
"""

from flask import Flask, request, render_template_string
import requests
from datetime import datetime
import os

app = Flask(__name__)

# ---------------------------
# Configuration serveur FHIR (Public ou Local)
# ---------------------------
# Remplace par ton URL Render ou HAPI FHIR public si besoin
URL_PATIENT = "https://hapi.fhir.org/baseR4/Patient"
URL_OBS = "https://hapi.fhir.org/baseR4/Observation"

# ---------------------------
# HTML & CSS Moderne
# ---------------------------
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>FHIR Health Connect</title>
    <style>
        :root { --primary: #2563eb; --bg: #f8fafc; --text: #1e293b; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: auto; }
        header { text-align: center; margin-bottom: 40px; }
        h1 { color: var(--primary); font-size: 2.5rem; margin-bottom: 5px; }
        
        .card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 30px; }
        h2 { border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; color: #334155; font-size: 1.2rem; }
        
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; }
        
        button { background: var(--primary); color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; transition: transform 0.2s, background 0.2s; }
        button:hover { background: #1d4ed8; transform: translateY(-2px); }
        
        .result-box { background: #f1f5f9; border-left: 5px solid var(--primary); padding: 20px; border-radius: 8px; margin-top: 20px; }
        .badge { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
        pre { background: #1e293b; color: #f8fafc; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>FHIR Health Connect</h1>
            <p>Gestion interopérable des données patients (HL7 FHIR)</p>
        </header>

        <div class="grid">
            <!-- Création Patient -->
            <div class="card">
                <h2>🧬 Nouveau Patient</h2>
                <form method="post" action="/create_patient">
                    <input name="family" placeholder="Nom de famille" required>
                    <input name="given" placeholder="Prénom" required>
                    <select name="gender">
                        <option value="male">Homme</option>
                        <option value="female">Femme</option>
                        <option value="other">Autre</option>
                    </select>
                    <input type="date" name="birthDate" required>
                    <button type="submit">Enregistrer le Patient</button>
                </form>
            </div>

            <!-- Création Observation -->
            <div class="card">
                <h2>💓 Nouvelle Observation</h2>
                <form method="post" action="/create_observation">
                    <input name="patient_id" placeholder="ID du Patient (ex: 123)" required>
                    <input type="number" name="value" placeholder="Fréquence Cardiaque (bpm)" required>
                    <button type="submit">Envoyer la Mesure</button>
                </form>
            </div>
        </div>

        <div class="card">
            <h2>🔍 Lecture & Mise à jour</h2>
            <form method="post" action="/manage_observation">
                <div style="display: flex; gap: 10px;">
                    <input name="obs_id" placeholder="ID de l'Observation" required>
                    <select name="action" style="width: 200px;">
                        <option value="get">Lire (Afficher)</option>
                        <option value="delete">Supprimer</option>
                    </select>
                </div>
                <button type="submit" style="background: #64748b;">Exécuter l'action</button>
            </form>
            
            <hr>
            
            <form method="post" action="/update_observation">
                <input name="obs_id" placeholder="ID de l'Observation à modifier" required>
                <input type="number" name="value" placeholder="Nouvelle valeur bpm" required>
                <button type="submit" style="background: #059669;">Mettre à jour la valeur</button>
            </form>
        </div>

        {% if result %}
        <div class="card result-box">
            <h2>📊 Résultat de l'opération</h2>
            <div>{{ result | safe }}</div>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# ---------------------------
# Fonctions Utilitaires d'affichage
# ---------------------------
def format_fhir_result(data, title="Détails"):
    """Transforme un JSON FHIR complexe en affichage HTML simple"""
    if isinstance(data, str): return f"<p>{data}</p>"
    
    html = f"<span class='badge'>{data.get('resourceType', 'Info')}</span>"
    
    if data.get("resourceType") == "Patient":
        name = data.get("name", [{}])[0]
        html += f"<h3>👤 Patient : {name.get('family', '').upper()} {name.get('given', [''])[0]}</h3>"
        html += f"<li>ID: <b>{data.get('id')}</b></li>"
        html += f"<li>Genre: {data.get('gender')}</li>"
        html += f"<li>Naissance: {data.get('birthDate')}</li>"
        
    elif data.get("resourceType") == "Observation":
        val = data.get("valueQuantity", {}).get("value")
        unit = data.get("valueQuantity", {}).get("unit")
        date = data.get("effectiveDateTime", "").replace("T", " à ")
        html += f"<h3>📈 Mesure : {val} {unit}</h3>"
        html += f"<li>ID Observation: <b>{data.get('id')}</b></li>"
        html += f"<li>Date: {date}</li>"
        html += f"<li>Sujet: {data.get('subject', {}).get('reference')}</li>"
    
    elif "issue" in data: # Cas d'erreur FHIR
        html = f"<p style='color:red;'>⚠️ Erreur : {data['issue'][0].get('diagnostics', 'Données invalides')}</p>"
    
    html += "<details><summary style='cursor:pointer; margin-top:10px; color:blue;'>Voir JSON brut</summary><pre>" + str(data) + "</pre></details>"
    return html

# ---------------------------
# Routes Flask
# ---------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)

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
        res_data = resp.json()
        result = format_fhir_result(res_data) if resp.status_code in [200, 201] else f"Erreur {resp.status_code}"
    except Exception as e:
        result = str(e)
    return render_template_string(HTML_PAGE, result=result)

@app.route("/create_observation", methods=["POST"])
def create_observation():
    data = request.form
    observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category","code": "vital-signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org","code": "8867-4","display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{data.get('patient_id')}"},
        "effectiveDateTime": datetime.now().isoformat(),
        "valueQuantity": {"value": int(data.get("value")), "unit": "bpm", "system": "http://unitsofmeasure.org", "code": "/min"}
    }
    try:
        resp = requests.post(URL_OBS, json=observation)
        result = format_fhir_result(resp.json())
    except Exception as e:
        result = str(e)
    return render_template_string(HTML_PAGE, result=result)

@app.route("/update_observation", methods=["POST"])
def update_observation():
    obs_id = request.form.get("obs_id")
    new_val = request.form.get("value")
    try:
        # 1. On récupère l'ancienne
        old = requests.get(f"{URL_OBS}/{obs_id}").json()
        # 2. On modifie la valeur
        old["valueQuantity"]["value"] = int(new_val)
        # 3. On renvoie (PUT)
        resp = requests.put(f"{URL_OBS}/{obs_id}", json=old)
        result = "✅ Mise à jour réussie : <br>" + format_fhir_result(resp.json())
    except:
        result = "❌ Erreur : ID introuvable ou serveur injoignable."
    return render_template_string(HTML_PAGE, result=result)

@app.route("/manage_observation", methods=["POST"])
def manage_observation():
    obs_id = request.form.get("obs_id")
    action = request.form.get("action")
    try:
        if action == "get":
            resp = requests.get(f"{URL_OBS}/{obs_id}")
            result = format_fhir_result(resp.json())
        else:
            requests.delete(f"{URL_OBS}/{obs_id}")
            result = f"🗑️ Observation {obs_id} supprimée avec succès."
    except:
        result = "Erreur lors de l'action."
    return render_template_string(HTML_PAGE, result=result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
