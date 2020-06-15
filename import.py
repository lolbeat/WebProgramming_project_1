import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    result = create_tables()
    if result:
        f = open("books.csv")
        reader = csv.reader(f)
        for isbn_import, title_import, author_import, year_import in reader:
            db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                {"isbn": isbn_import, "title": title_import, "author": author_import, "year": year_import})
            print(f"Book - Title: {title_import} Author: {author_import} Year: {year_import} ISBN: {isbn_import}")
        db.commit()
        print ("database entries committed")
    else:
        print("!!! Table Creation Issue !!!")

def create_tables():
    try:
        db.execute("CREATE TABLE books (isbn VARCHAR(10) PRIMARY KEY, title VARCHAR NOT NULL, author VARCHAR NOT NULL, year VARCHAR NOT NULL)")
        db.execute("CREATE TABLE users (user_id VARCHAR PRIMARY KEY, given_name VARCHAR NOT NULL, family_name VARCHAR NOT NULL, login_id VARCHAR NOT NULL, password VARCHAR NOT NULL)")
        db.execute("CREATE TABLE reviews (review_id SERIAL PRIMARY KEY, isbn VARCHAR(10) NOT NULL, user_id VARCHAR NOT NULL, user_rating INT NOT NULL, review_text VARCHAR(256), review_date DATE NOT NULL )")
        db.commit()
        print ("Tables Created")
        return True
    except:
        print("Tables NOT created")
        return False

if __name__ == "__main__":
    main()
