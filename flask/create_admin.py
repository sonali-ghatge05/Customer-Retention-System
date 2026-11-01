from werkzeug.security import generate_password_hash
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# create_admin.py
username = input("Enter admin username: ")
password = input("Enter admin password: ")
hashed = generate_password_hash(password)
print(f"Hash: {hashed}")

# Insert into database
connection = pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DB")
)
cursor = connection.cursor()
cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", 
               (username, hashed))
connection.commit()