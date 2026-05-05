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
    <title>FHIR Health Connect</title>
    <style>
        :root { --primary: #2563eb; --bg: #f8fafc; --text: #1e293b; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); padding: 20px; }
        .container { max-width: 900px; margin: auto; }
        .card { background: white; padding: 25px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h2 { border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }

        input, select {
            width: 100%;
            padding: 10px;
            margin: 6px 0;
            border-radius: 8px;
            border: 1px solid #ccc;
        }

        button {
            background: var(--primary);
            color: white;
            padding: 10px;
            border: none;
            border-radius: 8px;
            width: 100%;
            cursor: pointer;
        }

        button:hover { background: #1d4ed8; }

        .result-box {
            background: #f1f5f9;
            padding: 15px;
            border-left: 5px solid var(--primary);
            margin-top: 15px;
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
            <input type="date" name="birthDate" required>
            <button>Créer Patient</button>
        </form>
    </div>

    <div class="card">
        <h2>💓 Observation</h2>
        <form method="post" action="/create_observation">
            <input name="patient_id" placeholder="ID Patient" required>
            <input type="number" name="value" placeholder="BPM" required>
            <button>Créer Observation</button>
        </form>
    </div>

    <div class="card">
        <h2>🔧 Gestion Observation</h2>

        <form method="post" action="/manage_observation">
            <input name="obs_id" placeholder="ID observation" required>
            <select name="action">
                <option value="get">Lire</option>
                <option value="delete">Supprimer</option>
            </select>
            <button>Action</button>
        </form>

        <form method="get" action="/list_patients" style="margin-top:10px;">
            <button style="background:#7c3aed;">Voir patients</button>
        </form>

        <form method="post" action="/update_observation" style="margin-top:10px;">
            <input name="obs_id" placeholder="ID observation" required>
            <input type="number" name="value" placeholder="Nouvelle valeur" required>
            <button style="background:#059669;">Modifier</button>
        </form>
    </div>

    {% if result %}
    <div class="card result-box">
        <h2>Résultat</h2>
        <div>{{ result | safe }}</div>

        {% if patient_id %}
        <form method="post" action="/create_observation" style="margin-top:10px;">
            <input type="hidden" name="patient_id" value="{{ patient_id }}">
            <button>Créer observation pour ce patient</button>
        </form>
        {% endif %}
    </div>
    {% endif %}

</div>

</body>
</html>
"""

# ---------------------------
# Utils
# ---------------------------
def format_fhir(data):
    if isinstance(data, str):
        return f"<p>{data}</p>"

    html = f"<p><b>{data.get('resourceType')}</b></p>"

    if data.get("resourceType") == "Patient":
        name = data.get("name", [{}])[0]
        html += f"<p>{name.get('family','')} {name.get('given',[''])[0]}</p>"
        html += f"<p>ID: {data.get('id')}</p>"

    if data.get("resourceType") == "Observation":
        val = data.get("valueQuantity", {}).get("value")
        html += f"<p>Value: {val}</p>"

    return html

# ---------------------------
# ROUTES
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
        res = resp.json()
        result = format_fhir(res)

        patient_id = res.get("id")

    except Exception as e:
        result = str(e)
        patient_id = None

    return render_template_string(
        HTML_PAGE,
        result=result,
        patient_id=patient_id
    )

@app.route("/create_observation", methods=["POST"])
def create_observation():
    data = request.form

    try:
        value = int(data.get("value"))

        obs = {
            "resourceType": "Observation",
            "status": "final",
            "subject": {"reference": f"Patient/{data.get('patient_id')}"},
            "valueQuantity": {"value": value, "unit": "bpm"}
        }

        resp = requests.post(URL_OBS, json=obs)
        result = format_fhir(resp.json())

    except Exception as e:
        result = str(e)

    return render_template_string(HTML_PAGE, result=result)

@app.route("/update_observation", methods=["POST"])
def update_observation():
    obs_id = request.form.get("obs_id")
    value = request.form.get("value")

    try:
        value = int(value)

        old = requests.get(f"{URL_OBS}/{obs_id}").json()
        old["valueQuantity"]["value"] = value

        resp = requests.put(f"{URL_OBS}/{obs_id}", json=old)

        result = format_fhir(resp.json())

    except Exception as e:
        result = str(e)

    return render_template_string(HTML_PAGE, result=result)

@app.route("/manage_observation", methods=["POST"])
def manage_observation():
    obs_id = request.form.get("obs_id")
    action = request.form.get("action")

    try:
        if action == "get":
            data = requests.get(f"{URL_OBS}/{obs_id}").json()
            result = format_fhir(data)
        else:
            requests.delete(f"{URL_OBS}/{obs_id}")
            result = "Deleted"

    except Exception as e:
        result = str(e)

    return render_template_string(HTML_PAGE, result=result)

@app.route("/list_patients", methods=["GET"])
def list_patients():
    try:
        data = requests.get(URL_PATIENT).json()
        entries = data.get("entry", [])

        html = "<ul>"
        for e in entries:
            p = e["resource"]
            name = p.get("name", [{}])[0]
            html += f"<li>{name.get('family','')} {name.get('given',[''])[0]} - {p.get('id')}</li>"
        html += "</ul>"

    except Exception as e:
        html = str(e)

    return render_template_string(HTML_PAGE, result=html)

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
