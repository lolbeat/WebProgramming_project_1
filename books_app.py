import os

import requests, datetime
from flask import Flask, session, render_template, redirect, url_for, request, flash, abort, json, jsonify
from functools import wraps
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__, static_url_path='/static') #Need to set static path for image file
app.testing = True # needed for unit tests
app.secret_key = 'my_books_lolbeat' # needs encryption

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
#Session(app) # removed to enable flask session

# Set up database ###############################
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

if __name__=='__main__':
    app.run(debug=True)

################ function used by most routes - checks if user already in sessio
################ else redirect to login page
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'USERNAME' in session:
            return f(*args, **kwargs)
        else:
            flash ('Please login first')
            return redirect(url_for('login'))
    return wrap

################### index route ##
@app.route('/')
@login_required
def index():
    return render_template("book_search.html")

################### login route ######
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        #get userId and password and crosscheck with DB user table
        str_userid = request.form['username']
        str_password = request.form['password']
        user_info = db.execute("SELECT * FROM users WHERE user_id = :search_userid", {"search_userid":str_userid}).fetchone()
        if (user_info is None) or (user_info.password != str_password):
            message = 'User name or password not correct. Please try again.'
            return render_template("login.html", error = message)
        else:
            #if credentials ok then set session, flash user welcome and redirect to search page
            session['USERNAME'] = str_userid
            flash("Welcome. You're logged in")
            return redirect(url_for('search'))
    else:
        return render_template("login.html", error = 'Please submit the login form.')

################### logout #######
@app.route('/logout')
def logout():
    if 'USERNAME' in session :
        session.pop('USERNAME', None)
        flash('Bye! ...logged out')
    return redirect(url_for('login'))

################## search #####
# search for a particular book in our database and display the book_list page
@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    message = None
    books = []
    #check if POST & validate search criteria
    if request.method == 'POST':
        if request.form['book_title']== '' and request.form['book_author'] =='' and request.form['book_isbn']=='':
            message = 'Please enter something to search for...'
        else:
            try:
                #success - search database for book results
                #Note: search made case INsensitive by using ILIKE rather than LIKE
                if request.form['book_title'] != '':
                    books += db.execute("SELECT * FROM books WHERE title ILIKE :search_title", {"search_title":('%' + request.form['book_title'] + '%')}).fetchall()
                if request.form['book_author'] !='':
                    books += db.execute("SELECT * FROM books WHERE author ILIKE :search_author", {"search_author":('%' + request.form['book_author'] + '%')}).fetchall()
                if request.form['book_isbn'] !='':
                    books += db.execute("SELECT * FROM books WHERE isbn ILIKE :search_isbn", {"search_isbn":('%' + request.form['book_isbn'] + '%')}).fetchall()
                if not books:
                    message = "I didn't find any books matching your inputs. Please try again..."
            except:
                books=[]
                message = "Sorry, there was an error during our database search"
            if books:
                flash("Here's what I found...")
                return render_template("book_list.html", book_list = books)
    return render_template("book_search.html", error = message)         #if not POST then rerender the html page

############# display info on a single book #############
@app.route("/book/<isbn>")
@login_required
def book(isbn):
    review_list =[]
    # Make sure book exists.
    try:
        book_info = db.execute("SELECT * FROM books WHERE isbn = :my_isbn", {"my_isbn": isbn}).fetchone()
    except:
        message="Sorry, couldn't access the database for that ISBN...please try again later."
        return render_template("book_search.html", error = message)
    if book_info is None:
        return render_template("error.html", error="Sorry, that ISBN was not found.")
    # Get all reviews for this book
    try:
        review_list = db.execute("SELECT * FROM reviews WHERE isbn = :isbn",
                            {"isbn": isbn}).fetchall()
    except:
        flash("Sorry, Couldn't fetch book reviews")
    ratings_count, average_rating = goodreads_api(isbn)
    return render_template("book.html", book_info=book_info, reviews=review_list, ratings_count=ratings_count, average_rating=average_rating) #, reviews=reviews)

############### route for review edit #########################
@app.route("/book/review/<isbn>", methods=['GET', 'POST'])
@login_required
def review(isbn):
    if request.method == 'POST':
        #check mandatory fields are given and valid - further checks needed
        #rating defaulted to 1, input restricted to between 1 & 5
        user_rating = int(request.form['rating'])
        review_date = datetime.date.today()
        review_text= request.form['review_text']
        user_id = session['USERNAME']

        # Make sure book exists.
        try:
            book_info = db.execute("SELECT * FROM books WHERE isbn = :my_isbn", {"my_isbn": isbn}).fetchone()
        except:
            message="Sorry, couldn't access the database...please try again later."
            return render_template("book_search.html", error = message)

        if book_info is None:
            return render_template("error.html", error="Sorry, that ISBN was not found.")
        else:
            # Make sure that this user hasn't already reviewed this book
            try:
                review = db.execute("SELECT * FROM reviews WHERE isbn = :my_isbn AND user_id =:user_id", {"my_isbn": isbn, "user_id": user_id}).fetchone()
                if not review is None:
                    flash("SORRY: You can only review a book once. See your previous review below")
                    return redirect(url_for('book', isbn = isbn))
                else:
                    # insert user's form data into backend 'reviews' table
                    db.execute("INSERT INTO reviews (isbn, user_id, user_rating, review_text, review_date) VALUES (:isbn, :user_id, :user_rating, :review_text, :review_date)",
                    {"isbn": isbn, "user_id": user_id, "user_rating": user_rating, "review_text": review_text, "review_date": review_date })
                    db.commit()
            except:
                message ="Sorry, couldn't access the database...please try again later."
                return render_template("error.html", error=message)

        #redirect to search page when done
        flash('Thanks for your review !')
        return redirect(url_for('book', isbn = isbn))
    #not a post / error
    return render_template("review.html", error = "Please submit the form with your rating/review")

################## route for new user registration #########################

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        #check mandatory fields are given and valid - further checks needed
        #check userid is available
        if request.form['username']== '' or request.form['password1'] == '' or request.form['password2'] == '':
            message = 'Username and both password fields are mandatory'
        elif request.form['password1'] != request.form['password2']:
            message = 'Passwords not matching'
        else:
            try:
                db.execute("INSERT INTO users (user_id, given_name, family_name, password) VALUES (:uid, :frst, :scnd, :pw)",
                {"uid": request.form['username'], "frst": request.form['name_given'], "scnd": request.form['name_family'], "pw": request.form['password1']})
                db.commit()
                return redirect(url_for('search'))
            except:
                message="Sorry, there was an error creating your registration in our database...Please try again later."
    return render_template("register.html", error = message)

@app.errorhandler(404)
# inbuilt function which takes error as parameter
def page_not_found(e):
# defining function
    return render_template("404.html")

###################################################

#GET request to /api/<isbn> route should return a JSON response containing the
#book’s title, author, publication date, ISBN number, review count, and average
# score. Return 404 error if book not found in our DB
@app.route('/API/<book_isbn>')
@login_required
def api_getrequest(book_isbn):
    review_count, rating_total, rating_average = 0,0,0
    review_list=[]
    try:
        # Get all reviews for this book as well as the book info
        review_list = db.execute("SELECT * FROM reviews WHERE isbn = :isbn",
                            {"isbn": book_isbn}).fetchall()
        book = db.execute("SELECT * FROM books WHERE isbn = :search_isbn",
                            {"search_isbn":book_isbn }).fetchone()
    except:
        message="Sorry, Couldn't fetch book info...Please try again later."
        return render_template("error.html", error=message)
    # calculate total review count and average score and store as a dictionary
    for review in review_list:
        review_count+=1
        rating_total+= review[3]
    if not review_count == 0:
        rating_average = rating_total / review_count
    #get the book's basic info
    #book = db.execute("SELECT * FROM books WHERE isbn = :search_isbn", {"search_isbn":book_isbn }).fetchone()

    if book is None:
        abort(404) #abort to @app.errorhandler(404) 'page not found'
    else:
        #convert to dict & add review count & avg score
        book = dict(book)
        book.update({'review_count': review_count, 'average_score': rating_average})
        #turn JSON (dumps()) output into a Response object with the application/json mimetype
        return jsonify(book)

###################################################
#fetch book info from Goodreads API ***************
def goodreads_api(isbn):
    ratings_count, average_rating = 0, 0 # these values will be returned if any issue to get goodReads API data
    try:
        gr_response = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "Lu3MMRj0vB0nR60mU2kvw", "isbns": isbn})
        if not gr_response.status_code==200:
            flash("Sorry, we couldn't fetch any review info from 'goodReads'")
        else:
            try:
                gr_info = gr_response.json()
                ratings_count = gr_info['books'][0]['work_ratings_count']
                average_rating = gr_info['books'][0]['average_rating']
            except:
                flash("We couldn't understand the 'goodReads' book review info!")
    except:
        flash("Sorry, something went wrong contacting 'goodReads'.")
    return ratings_count, average_rating

    ###################################################
    ###################################################
