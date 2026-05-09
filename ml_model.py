from datetime import datetime

# ================= STOCK PREDICTION =================
def predict_stock_status(stock, daily_usage=5):

    if stock <= 0:
        return "OUT OF STOCK"

    days_left = stock / daily_usage

    if stock <= 10:
        return "CRITICAL STOCK - REORDER NOW"

    elif days_left <= 5:
        return "LOW STOCK - ORDER SOON"

    else:
        return "STOCK OK"


# ================= EXPIRY ALERT =================
def expiry_alert(expiry_date_str):

    try:
        expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
    except:
        return "INVALID DATE"

    today = datetime.today()
    days_left = (expiry_date - today).days

    if days_left < 0:
        return "EXPIRED"

    elif days_left <= 30:
        return f"EXPIRING SOON ({days_left} days)"

    elif days_left <= 90:
        return f"NEAR EXPIRY ({days_left} days)"

    else:
        return "SAFE"