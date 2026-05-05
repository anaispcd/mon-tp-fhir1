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
# HTML
# ---------------------------
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>FHIR Dashboard</title>
<style>
body { font-family: Arial; background:#f5f5f5; padding:20px; }
.card { background:white; padding:20px; margin-bottom:20px; border-radius:10px; }
button { width:100%; padding:10px; margin-top:10px; }
input, select { width:100%; padding:8px; margin-top:5px; }
</style>
</head>

<body>

<div class="card">
<h2>Créer Patient</h2>
<form method="post" action="/create_patient">
<input name="family" placeholder="Nom" required>
<input name="given" placeholder="Prénom" required>
<select name="gender">
<option value="male">Homme</option>
<option value="female">Femme</option>
<option value="other">Autre</option>
</select>
<input type="date" name="birthDate">
<button>Créer</button>
</form>
</div>

<div class="card">
<h2>Créer Observation</h2>
<form method="post" action="/create_observation">
<input name="patient_id" placeholder="Patient ID" required>
<input name="value" placeholder="BPM" required>
<button>Créer observation</button>
</form>
</div>

<div class="card">
<h2>Actions Observation</h2>

<form method="post" action="/manage_observation">
<input name="obs_id" placeholder="Observation ID">
<select name="action">
<option value="get">Lire</option>
<option value="delete">Supprimer</option>
</select>
<button>Action</button>
</form>

</div>

<div class="card">
<h2>Filtrer Patient (TES données)</h2>
<form method="get" action="/get_patient">
<input name="id" placeholder="Patient ID" required>
<button>Voir patient</button>
</form>

<form method="get" action="/get_observations">
<input name="id" placeholder="Patient ID" required>
<button>Voir observations patient</button>
</form>
</div>

{% if result %}
<div class="card">
<h2>Résultat</h2>
<div>{{ result | safe }}</div>
</div>
{% endif %}

</body>
</html>
"""

# ---------------------------
# FORMAT
# ---------------------------
def fmt(data):
    if isinstance(data, str):
        return data
    return f"<pre>{data}</pre>"

# ---------------------------
# ROUTES
# ---------------------------
@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_PAGE)

# CREATE PATIENT
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

    patient_id = res.get("id")

    return render_template_string(
        HTML_PAGE,
        result=f"Patient créé ID: {patient_id}",
        patient_id=patient_id
    )

# CREATE OBSERVATION
@app.route("/create_observation", methods=["POST"])
def create_observation():
    data = request.form

    try:
        obs = {
            "resourceType": "Observation",
            "status": "final",
            "subject": {"reference": f"Patient/{data.get('patient_id')}"},
            "valueQuantity": {"value": int(data.get("value")), "unit": "bpm"}
        }

        resp = requests.post(URL_OBS, json=obs)
        res = resp.json()

        return render_template_string(HTML_PAGE, result=f"Observation créée ID: {res.get('id')}")

    except Exception as e:
        return render_template_string(HTML_PAGE, result=str(e))

# GET PATIENT (FILTRÉ)
@app.route("/get_patient", methods=["GET"])
def get_patient():
    pid = request.args.get("id")

    resp = requests.get(f"{URL_PATIENT}?_id={pid}")
    data = resp.json()

    return render_template_string(HTML_PAGE, result=data)

# GET OBSERVATIONS FOR PATIENT (IMPORTANT)
@app.route("/get_observations", methods=["GET"])
def get_obs():
    pid = request.args.get("id")

    resp = requests.get(f"{URL_OBS}?subject=Patient/{pid}")
    data = resp.json()

    return render_template_string(HTML_PAGE, result=data)

# MANAGE OBS
@app.route("/manage_observation", methods=["POST"])
def manage():
    obs_id = request.form.get("obs_id")
    action = request.form.get("action")

    if action == "get":
        data = requests.get(f"{URL_OBS}/{obs_id}").json()
        return render_template_string(HTML_PAGE, result=data)

    requests.delete(f"{URL_OBS}/{obs_id}")
    return render_template_string(HTML_PAGE, result="deleted")

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
