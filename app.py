import os
import requests
from bs4 import BeautifulSoup
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import time

# ===============================================
# FLASK APP SETUP
# ===============================================
app = Flask(__name__)
CORS(app)  # ✅ CORS ENABLED (THIS FIXES HTML ERROR)

# ===============================================
# CONFIGURATION
# ===============================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36",
    "Referer": "https://vahanx.in/",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

# Railway / Render / VPS compatible port
FLASK_PORT = int(os.environ.get("PORT", 8080))

# ===============================================
# VEHICLE INFO SCRAPER
# ===============================================
def get_comprehensive_vehicle_details(rc_number: str) -> dict:
    rc = rc_number.strip().upper()
    url = f"https://vahanx.in/rc-search/{rc}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        return {"error": f"Failed to fetch data: {str(e)}"}

    def extract_card(label):
        for div in soup.select(".hrcd-cardbody"):
            span = div.find("span")
            if span and label.lower() in span.text.lower():
                p = div.find("p")
                return p.get_text(strip=True) if p else None
        return None

    def extract_from_section(header_text, keys):
        section = soup.find("h3", string=lambda s: s and header_text.lower() in s.lower())
        section_card = section.find_parent("div", class_="hrc-details-card") if section else None
        result = {}
        for key in keys:
            span = section_card.find("span", string=lambda s: s and key.lower() in s.lower()) if section_card else None
            if span:
                val = span.find_next("p")
                result[key.lower().replace(" ", "_")] = val.get_text(strip=True) if val else None
        return result

    def get_value(label):
        span = soup.find("span", string=lambda s: s and label.lower() in s.lower())
        if span:
            p = span.find_next("p")
            return p.get_text(strip=True) if p else None
        return None

    insurance_expired_box = soup.select_one(".insurance-alert-box.expired .title")
    expired_days = None
    if insurance_expired_box:
        m = re.search(r"(\d+)", insurance_expired_box.text)
        expired_days = int(m.group(1)) if m else None

    data = {
        "status": "success",
        "registration_number": rc,

        "basic_info": {
            "owner_name": extract_card("Owner Name") or get_value("Owner Name"),
            "father_name": get_value("Father's Name"),
            "model_name": extract_card("Model Name") or get_value("Model Name"),
            "vehicle_class": get_value("Vehicle Class"),
            "fuel_type": get_value("Fuel Type"),
            "city": extract_card("City Name") or get_value("City Name"),
            "address": extract_card("Address") or get_value("Address"),
        },

        "vehicle_details": extract_from_section("Vehicle Details", [
            "Maker Model", "Cubic Capacity", "Seating Capacity", "Fuel Norms"
        ]),

        "insurance": {
            "status": "Expired" if expired_days else "Active",
            "company": get_value("Insurance Company"),
            "policy_number": get_value("Insurance No"),
            "valid_upto": get_value("Insurance Upto"),
            "expired_days_ago": expired_days
        },

        "validity": {
            "registration_date": get_value("Registration Date"),
            "fitness_upto": get_value("Fitness Upto"),
            "tax_upto": get_value("Tax Upto")
        },

        "puc": {
            "puc_no": get_value("PUC No"),
            "puc_upto": get_value("PUC Upto")
        },

        "other_info": {
            "financer": get_value("Financier Name"),
            "permit_type": get_value("Permit Type"),
            "blacklist_status": get_value("Blacklist Status"),
            "noc": get_value("NOC Details")
        },

        "credit": {
            "developer": "@indian_methods",
            "platform": "GitHub",
            "source": "vahanx.in",
            "note": "For educational & informational use only"
        }
    }

    # remove empty values
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items() if v not in [None, "", {}]}
        return obj

    return clean(data)

# ===============================================
# API ROUTES
# ===============================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "service": "Vehicle Information API",
        "developer": "@indian_methods",
        "endpoint": "/api/vehicle-info?rc=DL01AB1234"
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": time.time()
    })

@app.route("/api/vehicle-info", methods=["GET"])
def vehicle_info():
    rc = request.args.get("rc")
    if not rc:
        return jsonify({
            "error": "Missing rc parameter",
            "usage": "/api/vehicle-info?rc=DL01AB1234"
        }), 400

    data = get_comprehensive_vehicle_details(rc)
    if data.get("error"):
        return jsonify(data), 404

    return jsonify(data)

# ===============================================
# MAIN
# ===============================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT)
