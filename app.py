from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os
import re
import pandas as pd
from werkzeug.utils import secure_filename

from db import (
    insert_user,
    get_user,
    insert_medicine,
    get_all_medicines,
    delete_medicine
)

# ================= OCR =================
try:
    from ocr_engine import extract_text, extract_expiry

except Exception as e:

    print("OCR IMPORT ERROR:", e)

    def extract_text(path):
        return ""

    def extract_expiry(text):
        return None

# ================= ML =================
try:
    from ml_model import predict_stock_status, expiry_alert

except Exception as e:

    print("ML IMPORT ERROR:", e)

    def predict_stock_status(stock):
        return "OK"

    def expiry_alert(expiry):
        return "UNKNOWN"

# ================= APP SETUP =================
app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "medicine_project_key"
)

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= CSV DATABASE =================
CSV_PATH = "medicines.csv"


def load_medicine_db():

    try:

        if not os.path.exists(CSV_PATH):

            print("CSV FILE NOT FOUND")

            return []

        df = pd.read_csv(CSV_PATH)

        # Clean column names
        df.columns = [
            c.strip().lower()
            for c in df.columns
        ]

        print("CSV COLUMNS:", df.columns.tolist())

        if "medicine_name" not in df.columns:

            print("medicine_name COLUMN NOT FOUND")

            return []

        medicines = (
            df["medicine_name"]
            .dropna()
            .astype(str)
            .str.strip()
            .tolist()
        )

        # Remove duplicates
        medicines = list(set(medicines))

        return medicines

    except Exception as e:

        print("CSV LOAD ERROR:", e)

        return []


medicine_database = load_medicine_db()

print("TOTAL MEDICINES LOADED:", len(medicine_database))

# ================= MEDICINE DETECTION =================
def detect_medicine(text):

    if not text:
        return "Unknown Medicine"

    raw_text = text.lower()

    # Clean OCR text
    clean_text = re.sub(
        r'[^a-z0-9 ]',
        ' ',
        raw_text
    )

    clean_text = re.sub(
        r'\s+',
        ' ',
        clean_text
    ).strip()

    print("OCR CLEAN TEXT:", clean_text)

    # ================= OCR CORRECTIONS =================
    corrections = {

        "porocetomol": "paracetamol",
        "parocetamol": "paracetamol",
        "paracetomol": "paracetamol",
        "paracitamol": "paracetamol",

        "dol0": "dolo",
        "doio": "dolo",

        "tublets": "tablets",
        "tabiets": "tablets"
    }

    for wrong, correct in corrections.items():

        clean_text = clean_text.replace(
            wrong,
            correct
        )

    print("CORRECTED OCR:", clean_text)

    # ================= EXTRACT IMPORTANT PART =================
    stop_words = [
        "ip",
        "mg",
        "tablets",
        "tablet",
        "capsules",
        "capsule"
    ]

    important_text = clean_text

    for stop in stop_words:

        if stop in clean_text:

            important_text = clean_text.split(stop)[0]

            break

    print("IMPORTANT TEXT:", important_text)

    # ================= DIRECT MATCH =================
    for med in medicine_database:

        med_lower = med.lower().strip()

        if med_lower in important_text:

            print("DIRECT MATCH:", med)

            return med

    # ================= WORD MATCH =================
    words = important_text.split()

    for word in words:

        if len(word) < 4:
            continue

        for med in medicine_database:

            med_lower = med.lower()

            # Exact match
            if word == med_lower:

                print("EXACT MATCH:", med)

                return med

            # Strong beginning match
            if med_lower.startswith(word[:5]):

                print("START MATCH:", med)

                return med

    print("NO MATCH FOUND")

    return "Unknown Medicine"
# ================= HOME =================
@app.route('/')
def login():

    return render_template("login.html")

# ================= LOGIN =================
@app.route('/login', methods=['POST'])
def login_check():

    email = request.form.get("email")

    password = request.form.get("password")

    user = get_user(email)

    if user and user.get("password") == password:

        session["user"] = email

        return redirect(
            url_for("upload_page")
        )

    return render_template(
        "login.html",
        error="Invalid login"
    )

# ================= REGISTER =================
@app.route('/register', methods=['POST'])
def register():

    email = request.form.get("email")

    if get_user(email):

        return render_template(
            "login.html",
            error="User already exists"
        )

    insert_user({
        "name": request.form.get("name"),
        "email": email,
        "phone": request.form.get("phone"),
        "password": request.form.get("password")
    })

    return render_template(
        "login.html",
        success="Registration Successful!"
    )

# ================= UPLOAD PAGE =================
@app.route('/upload_page')
def upload_page():

    if "user" not in session:

        return redirect(url_for("login"))

    return render_template("index.html")

# ================= FILE UPLOAD =================
@app.route('/upload', methods=['POST'])
def upload():

    if "user" not in session:

        return redirect(url_for("login"))

    file = request.files.get("file")

    if not file or file.filename == "":

        return "No file selected"

    try:

        # Save image
        filename = secure_filename(file.filename)

        filepath = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        file.save(filepath)

        # ================= OCR =================
        text = extract_text(filepath)

        print("OCR RAW TEXT:", text)

        # ================= DETECT MEDICINE =================
        ocr_name = detect_medicine(text)

        # ================= DETECT EXPIRY =================
        ocr_expiry = extract_expiry(text)

        # ================= FORM VALUES =================
        name = (
            request.form.get("manual_name")
            or ocr_name
        )

        expiry = (
            request.form.get("manual_expiry")
            or ocr_expiry
        )

        stock_val = request.form.get("stock")

        stock = (
            int(stock_val)
            if stock_val and stock_val.isdigit()
            else 10
        )

        # ================= INSERT INTO DATABASE =================
        insert_medicine({

            "medicine_name": name,

            "stock": stock,

            "expiry_date": expiry,

            "order_date": datetime.now().strftime(
                "%d-%m-%Y"
            ),

            "image": filename,

            "stock_status": predict_stock_status(stock),

            "expiry_status": (
                expiry_alert(expiry)
                if expiry
                else "UNKNOWN"
            )
        })

        return redirect(
            url_for("dashboard")
        )

    except Exception as e:

        print("UPLOAD ERROR:", e)

        return f"Error: {e}"

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if "user" not in session:

        return redirect(url_for("login"))

    medicines = get_all_medicines()

    low_stock = []

    expiring = []

    today = datetime.now().date()

    for m in medicines:

        # ================= LOW STOCK =================
        try:

            if int(m.get("stock", 0)) <= 5:

                low_stock.append(
                    m.get("medicine_name")
                )

        except:
            pass

        # ================= EXPIRY CHECK =================
        expiry_str = m.get("expiry_date")

        if expiry_str:

            try:

                exp_date = datetime.strptime(
                    expiry_str,
                    "%Y-%m-%d"
                ).date()

                days_left = (
                    exp_date - today
                ).days

                if 0 <= days_left <= 30:

                    expiring.append(
                        f"{m['medicine_name']} "
                        f"({days_left} days left)"
                    )

                m["display_expiry"] = (
                    exp_date.strftime("%d-%m-%Y")
                )

            except:

                m["display_expiry"] = expiry_str

        else:

            m["display_expiry"] = "N/A"

    return render_template(

        "dashboard.html",

        medicines=medicines,

        popup_msg=(
            "\n".join(expiring)
            if expiring else None
        ),

        low_stock_msg=(
            ", ".join(low_stock)
            if low_stock else None
        )
    )

# ================= DELETE =================
@app.route('/delete/<id>')
def delete(id):

    delete_medicine(id)

    return redirect(
        url_for("dashboard")
    )

# ================= LOGOUT =================
@app.route('/logout')
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )

# ================= RUN =================
if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )