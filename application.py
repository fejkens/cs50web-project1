import os
import requests
import json

from flask import Flask, session, render_template, request, redirect, url_for, Response
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

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
  	# If user is already logged in render the index page
    return render_template("index.html", username=session["username"])
  else:
  	# Otherwise redirect to login page
    return redirect(url_for("login"))
  
@app.route("/login", methods=["GET", "POST"])
def login():

  if request.method == "GET":
  	# If GET request, render the login page
    return render_template("login.html")
  else:
    # Otherwise check if user is registered
    if not db.execute("SELECT username FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchone():
      return render_template("error.html", error="You're not registered")
    
    # If user is registered, check the password
    if check_password_hash(db.execute("SELECT password FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchone()[0], request.form.get("password")):
      # If password correct, log the user in and redirect to index page
      session["username"] = request.form.get("username")
      return redirect(url_for("index"))
    
    # Otherwise, return error
    return render_template("error.html", error="Wrong password")
  
@app.route("/logout")
def logout():

	# Clear the user from the session and redirect to the login page
  session.pop("username", None)
  return redirect(url_for("login"))
  
@app.route("/register", methods=["GET", "POST"])
def register():

	# If GET request, render the register page
  if request.method == "GET":
    return render_template("register.html")
  
  username = request.form.get("username")
  password = generate_password_hash(request.form.get("password"))
  confirmation = generate_password_hash(request.form.get("confirmation"))
  
  if len(request.form.get("password")) < 5:
  	return render_template("error.html", error="Password too short")

  # Check if fields filled in
  if not username or not password or not confirmation:
    return render_template("error.html", error="Fields are missing")
  
  # Check if passwords match
  if not request.form.get("password") == request.form.get("confirmation"):
    return render_template("error.html", error="Passwords do not match")
  
  # Check if username does not exists in the database
  if not db.execute("SELECT UPPER(username) FROM users WHERE UPPER(username) = UPPER(:username)", {"username": username}).first():
    
    # Insert the user into the table
    db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": password})
    db.commit()
    
    # Log the user in and redirect to index page
    session["username"] = username
    return redirect(url_for("index"))
  
  else:

  	# Return already registered
    return render_template("error.html", error="Already registered")

@app.route("/search", methods=["POST"])
def search():

	# Prepare search variables, search for exact results and search2 for similar results
  search = request.form.get("search")
  search2 = "%" + search + "%"
  
  # Search query
  result = db.execute(
    "SELECT * FROM books WHERE UPPER(isbn) = UPPER(:search) OR UPPER(title) = UPPER(:search) OR UPPER(author) = UPPER(:search) UNION SELECT * FROM books WHERE UPPER(isbn) LIKE UPPER(:search) OR UPPER(title) LIKE UPPER(:search) OR UPPER(author) LIKE UPPER(:search) UNION SELECT * FROM books WHERE UPPER(isbn) LIKE UPPER(:search2) OR UPPER(title) LIKE UPPER(:search2) OR UPPER(author) LIKE UPPER(:search2)",{"search": search, "search2": search2}).fetchall()

  # If no results found
  if not result:
    return render_template("error.html", error="No results found")
  
  # Render the results page
  return render_template("searchresults.html", result=result)

@app.route("/book/<isbn>")
def book(isbn):

  # Take isbn and return book info
  result = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()

  if not result:
      return render_template("error.html", error="Book info not found")

  # Check if user submitted a review for this book

  userid = db.execute("SELECT userid FROM users WHERE username = :username", {"username": session["username"]}).fetchone()[0]
  bookid = db.execute("SELECT book_id FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()[0]

  review = db.execute("SELECT * FROM reviews WHERE user_id = :userid AND book_id = :book_id", {"userid": userid, "book_id": bookid}).fetchone()

  showreviewbox = 0

  # If no reviews submitted, show the review box on the page
  if not review:
      showreviewbox = 1

  # Fetch goodreads data for the book
  res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "qa0oeL0h0XP2WUrWWLekhw", "isbns": isbn}).json()
  ratingsCount = res["books"][0]["work_ratings_count"]
  avScore = res["books"][0]["average_rating"]

  return render_template("book.html", result=result, showreviewbox=showreviewbox, review=review, isbn=isbn, ratingsCount=ratingsCount, avScore=avScore)

@app.route("/submitreview", methods=["POST"])
def submitreview():

	# Get the book and user ids
  bookid = db.execute('SELECT "book_id" FROM books WHERE isbn = :isbn', {"isbn": request.form.get("isbn")}).fetchone()[0]
  userid = db.execute('SELECT userid FROM users WHERE username = :username', {"username": session["username"]}).fetchone()[0]

  # Submit the review
  db.execute('INSERT INTO reviews ("book_id", "user_id", "score", "review") VALUES (:bookid, :userid, :score, :review)', {"bookid": bookid, "userid": userid, "score": request.form.get("score"), "review": request.form.get("review")})
  db.commit()

  # Return to the page
  return redirect(url_for("book", isbn=request.form.get("isbn")))

@app.route("/api/<isbn>")
def api(isbn):
  
  book = db.execute('SELECT * FROM books WHERE isbn = :isbn', {"isbn": isbn}).fetchall()[0]

  res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "qa0oeL0h0XP2WUrWWLekhw", "isbns": isbn}).json()
  ratingsCount = res["books"][0]["work_ratings_count"]
  avScore = res["books"][0]["average_rating"]
  
  result = [{
    "title": book.title,
    "author": book.author,
    "year": book.year,
    "isbn": book.isbn,
    "review_count": ratingsCount,
    "average_score": avScore
  }]

  return app.response_class(json.dumps(result), status=200, mimetype='application/json')








