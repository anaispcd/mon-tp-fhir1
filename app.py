from flask import Flask, request, render_template_string
import requests
from datetime import datetime
import os

app = Flask(__name__)

# ---------------------------
# FHIR SERVER
# ---------------------------
URL_PATIENT = "https://hapi.fhir.org/baseR4/Patient"
URL_OBS = "https://hapi.fhir.org/baseR4/Observation"

# ---------------------------
# HTML + CSS
# ---------------------------
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>FHIR Dashboard</title>

<style>
body {
    font-family: Arial, sans-serif;
    background: #f4f6f9;
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 1000px;
    margin: auto;
}

.card {
    background: white;
    padding: 20px;
    margin-bottom: 15px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

h2 {
    margin-top: 0;
    color: #1f3c88;
}

input, select {
    width: 100%;
    padding: 10px;
    margin-top: 6px;
    margin-bottom: 10px;
    border-radius: 8px;
    border: 1px solid #ccc;
}

button {
    width: 100%;
    padding: 10px;
    border: none;
    border-radius: 8px;
    background: #2563eb;
    color: white;
    font-weight: bold;
    cursor: pointer;
}

button:hover {
    background: #1d4ed8;
}

.obs {
    border-left: 5px solid #2563eb;
    padding: 10px;
    margin-bottom: 10px;
    background: #f9fbff;
}

.patient {
    border-left: 5px solid #16a34a;
    padding: 10px;
    margin-bottom: 10px;
    background: #f6fff8;
}
</style>

</head>

<body>
<div class="container">

<div class="card">
<h2>🧬 Nouveau Patient</h2>
<form method="post" action="/create_patient">
<input name="family" placeholder="Nom" required>
<input name="given" placeholder="Prénom" required>
<select name="gender">
<option value="male">Homme</option>
<option value="female">Femme</option>
<option value="other">Autre</option>
</select>
<input type="date" name="birthDate">
<button>Créer Patient</button>
</form>
</div>

<div class="card">
<h2>💓 Nouvelle Observation</h2>
<form method="post" action="/create_observation">
<input name="patient_id" placeholder="ID Patient" required>
<input name="value" placeholder="BPM" required>
<button>Créer Observation</button>
</form>
</div>

<div class="card">
<h2>🔧 Actions Observation</h2>

<form method="post" action="/manage_observation">
<input name="obs_id" placeholder="ID Observation">
<select name="action">
<option value="get">Lire</option>
<option value="delete">Supprimer</option>
</select>
<button>Action</button>
</form>

</div>

<div class="card">
<h2>🔎 Recherche</h2>

<form method="get" action="/get_patient">
<input name="id" placeholder="Patient ID">
<button>Voir patient</button>
</form>

<form method="get" action="/get_observations">
<input name="id" placeholder="Patient ID">
<button>Voir observations</button>
</form>

</div>

<!-- ✅ AJOUT : BASE DE DONNÉES VISUELLE -->
<div class="card">
<h2>📌 Base de données (rappel IDs)</h2>

{{ patients | safe }}

{{ observations | safe }}

</div>

{% if result %}
<div class="card">
<h2>Résultat</h2>
<div>{{ result | safe }}</div>
</div>
{% endif %}

</div>
</body>
</html>
"""

# ---------------------------
# FORMAT FHIR CLEAN
# ---------------------------
def format_bundle(bundle):
    if not isinstance(bundle, dict):
        return str(bundle)

    entries = bundle.get("entry", [])

    if not entries:
        return "<p>Aucun résultat</p>"

    html = ""

    for e in entries:
        res = e.get("resource", {})

        if res.get("resourceType") == "Patient":
            name = res.get("name", [{}])[0]
            html += f"""
            <div class="patient">
                👤 <b>Patient</b><br>
                ID: {res.get('id')}<br>
                Nom: {name.get('family','')} {name.get('given',[''])[0]}
            </div>
            """

        elif res.get("resourceType") == "Observation":
            val = res.get("valueQuantity", {}).get("value")
            unit = res.get("valueQuantity", {}).get("unit")

            html += f"""
            <div class="obs">
                📊 <b>Observation</b><br>
                ID: {res.get('id')}<br>
                Patient: {res.get('subject', {}).get('reference')}<br>
                Valeur: {val} {unit}
            </div>
            """

    return html

# ---------------------------
# AJOUT LISTES PERMANENTES
# ---------------------------
def list_patients():
    try:
        resp = requests.get(URL_PATIENT + "?_count=10")
        data = resp.json()

        html = "<h3>👤 Patients enregistrés</h3>"

        for e in data.get("entry", []):
            p = e.get("resource", {})
            name = p.get("name", [{}])[0]

            html += f"""
            <div class="patient">
                {name.get('family','')} {name.get('given',[''])[0]}<br>
                ID : <b>{p.get('id')}</b>
            </div>
            """

        return html
    except:
        return "<p>Erreur chargement patients</p>"


def list_observations():
    try:
        resp = requests.get(URL_OBS + "?_count=10")
        data = resp.json()

        html = "<h3>📊 Observations récentes</h3>"

        for e in data.get("entry", []):
            o = e.get("resource", {})

            html += f"""
            <div class="obs">
                ID : <b>{o.get('id')}</b><br>
                Patient : {o.get('subject', {}).get('reference')}<br>
                Valeur : {o.get('valueQuantity', {}).get('value')}
            </div>
            """

        return html
    except:
        return "<p>Erreur chargement observations</p>"

# ---------------------------
# ROUTES
# ---------------------------

@app.route("/", methods=["GET"])
def index():
    patients = list_patients()
    observations = list_observations()

    return render_template_string(
        HTML_PAGE,
        patients=patients,
        observations=observations
    )

@app.route("/create_patient", methods=["POST"])
def create_patient():
    data = request.form

    patient = {
        "resourceType": "Patient",
        "name": [{"family": data.get("family"), "given": [data.get("given")]}],
        "gender": data.get("gender"),
        "birthDate": data.get("birthDate")
    }

    resp = requests.post(URL_PATIENT, json=patient)
    res = resp.json()

    return render_template_string(HTML_PAGE, result=f"Patient créé ID: {res.get('id')}")

@app.route("/create_observation", methods=["POST"])
def create_observation():
    data = request.form

    try:
        obs = {
            "resourceType": "Observation",
            "status": "final",
            "subject": {"reference": f"Patient/{data.get('patient_id')}"},
            "valueQuantity": {
                "value": int(data.get("value")),
                "unit": "bpm"
            }
        }

        resp = requests.post(URL_OBS, json=obs)
        res = resp.json()

        return render_template_string(
            HTML_PAGE,
            result=f"Observation créée ID: {res.get('id')}"
        )

    except Exception as e:
        return render_template_string(HTML_PAGE, result=str(e))

@app.route("/get_patient", methods=["GET"])
def get_patient():
    pid = request.args.get("id")

    resp = requests.get(f"{URL_PATIENT}?_id={pid}")
    data = resp.json()

    return render_template_string(
        HTML_PAGE,
        result=format_bundle(data)
    )

@app.route("/get_observations", methods=["GET"])
def get_observations():
    pid = request.args.get("id")

    resp = requests.get(f"{URL_OBS}?subject=Patient/{pid}")
    data = resp.json()

    return render_template_string(
        HTML_PAGE,
        result=format_bundle(data)
    )

@app.route("/manage_observation", methods=["POST"])
def manage():
    obs_id = request.form.get("obs_id")
    action = request.form.get("action")

    try:
        if action == "get":
            data = requests.get(f"{URL_OBS}/{obs_id}").json()
            return render_template_string(
                HTML_PAGE,
                result=format_bundle({"entry":[{"resource":data}]})
            )

        requests.delete(f"{URL_OBS}/{obs_id}")
        return render_template_string(HTML_PAGE, result="Observation supprimée")

    except Exception as e:
        return render_template_string(HTML_PAGE, result=str(e))

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
