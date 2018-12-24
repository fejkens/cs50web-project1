import os

from flask import Flask, session, render_template, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
  raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.secret_key = b'_5#y2L"F4Q8z\n\xad]/'

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
  return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
  if request.method == "GET":
    return render_template("register.html")
  
  username = request.form.get("username")
  password = request.form.get("password")
  confirmation = request.form.get("confirmation")
  
  # Check if fields filled in
  if not username or not password or not confirmation:
    return "Missing fields"
  
  # Check if passwords match
  if not password == confirmation:
    return "Passwords do not match"
  
  # Check if username does not exists in the database
  if not db.execute("SELECT username FROM users WHERE username = :username", {"username": username}).first():
    
    # Insert the user into the table
    db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": password})
    
    db.commit()
    
    # Return to index
    return redirect(url_for("index"))
  
  # Check if username already exists in the database
  if db.execute("SELECT username FROM users WHERE username = :username", {"username": username}).first()[0] == username:
    
    # Return already registered
    return "Already registered"