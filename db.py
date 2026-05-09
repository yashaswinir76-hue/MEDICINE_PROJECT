from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv

# ---------------- CONNECTION ----------------
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise Exception("MONGO_URI NOT FOUND in environment variables")

client = MongoClient(MONGO_URI)
db = client["mediscan"]

users_col = db["users"]
medicines_col = db["medicines"]

# ---------------- USERS ----------------

def insert_user(data):
    users_col.insert_one(data)

def get_user(email):
    return users_col.find_one({"email": email})

# ---------------- MEDICINES ----------------

def insert_medicine(data):
    medicines_col.insert_one(data)

def get_all_medicines():
    data = list(medicines_col.find())
    
    # Convert ObjectId → string for frontend
    for d in data:
        d["_id"] = str(d["_id"])
    
    return data

def delete_medicine(mid):
    medicines_col.delete_one({"_id": ObjectId(mid)})