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


@app.route("/", methods=["GET", "POST"])
def index():
  if "username" in session:
    return render_template("index.html", username=session["username"])
  else:
    return redirect(url_for("login"))
  
@app.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "GET":
    return render_template("login.html")
  else:
    # Check if registered
    if not db.execute("SELECT username FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchone():
      return "You're not registered!"
    
    username = request.form.get("username")
    
    if db.execute("SELECT password FROM users WHERE username = :username", {"username": username}).fetchone()[0] == request.form.get("password"):
      # Correct pass
      session["username"] = request.form.get("username")
      return redirect(url_for("index"))
    
    return "Wrong password"
  
@app.route("/logout")
def logout():
  session.pop("username", None)
  return redirect(url_for("login"))
  
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
    
    session["username"] = username
    
    # Return to index
    return redirect(url_for("index"))
  
  # Check if username already exists in the database
  if db.execute("SELECT username FROM users WHERE username = :username", {"username": username}).first()[0] == username:
    
    # Return already registered
    return "Already registered"
  
@app.route("/search", methods=["POST"])
def search():
  search = request.form.get("search")
  search2 = "%" + search + "%"
  
  result = db.execute(
    "SELECT * FROM books WHERE UPPER(isbn) = UPPER(:search) OR UPPER(title) = UPPER(:search) OR UPPER(author) = UPPER(:search) UNION SELECT * FROM books WHERE UPPER(isbn) LIKE UPPER(:search) OR UPPER(title) LIKE UPPER(:search) OR UPPER(author) LIKE UPPER(:search) UNION SELECT * FROM books WHERE UPPER(isbn) LIKE UPPER(:search2) OR UPPER(title) LIKE UPPER(:search2) OR UPPER(author) LIKE UPPER(:search2)",{"search": search, "search2": search2}).fetchall()

  if not result:
    return render_template("error.html", error="No results found")
  
  return render_template("searchresults.html", result=result)

@app.route("/book/<isbn>")
def book(isbn):
	# take isbn and return book info
	result = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn})

	if not result:
		return render_template("error.html", error="Book info not found")

	return render_template("book.html", result=result)
















