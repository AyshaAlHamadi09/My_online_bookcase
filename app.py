import os
from datetime import datetime
import requests
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
from flask import Flask, render_template, request
from data_models import db, Author, Book

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data/library.sqlite')

db.init_app(app)

with app.app_context():
    db.create_all()


def get_cover_image_url(book_title):
    """
    takes a book's title and retrieves the book's cover image URL from google's book API
    """
    url = f'https://www.googleapis.com/books/v1/volumes?q={book_title}'
    book_info_dict = requests.get(url, timeout=5).json()
    book_cover_image_url = book_info_dict['items'][0]['volumeInfo']['imageLinks']['thumbnail'] \
        if 'imageLinks' in book_info_dict['items'][0]['volumeInfo'] else ''
    return book_cover_image_url


@app.route('/')
def index():
    books = Book.query.order_by(Book.title.asc()).all()
    return render_template('home.html', books=books)

@app.route('/search_book', methods=['POST'])
def search_book():
    search_keyword = request.form.get('search')
    books = Book.query.filter(Book.title.like(f'%{search_keyword}%')).all()
    message = ''

    if not books:
        message = f'There were no books that match {search_keyword}.'

    return render_template('home.html', message=message, books=books)

def create_new_author():
    name = request.form.get('name')
    birth_date_str = request.form.get('birthdate')
    birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
    death_date_str = request.form.get('date_of_death')

    date_of_death = None
    if death_date_str:
        date_of_death = datetime.strptime(death_date_str, '%Y-%m-%d').date()

    return Author(name=name,birth_date=birth_date,date_of_death=date_of_death)

@app.route('/authors', methods=['GET', 'POST'])
def add_author():
    """
    Add a new authors route
    """
    if request.method == 'POST':
        try:
            new_author = create_new_author()
            db.session.add(new_author)
            db.session.commit()
            message = 'Author has successfully added to the database.'
        except SQLAlchemyError:
            db.session.rollback()
            message = 'Failed to add author to the database.'
        return render_template('add_author.html', message=message)

    return render_template('add_author.html')


@app.route('/books', methods=['GET','POST'])
def add_book():
    message = ''
    if request.method == 'POST':
        try:
            book_title = request.form.get('title')
            new_book = Book(
                isbn=request.form.get('isbn'),
                title=book_title,
                publication_year=request.form.get('publication_year'),
                cover_image_url=get_cover_image_url(book_title),
                author_id=request.form.get('author')
            )
            db.session.add(new_book)
            db.session.commit()
            message = 'Book has successfully been added to the database.'
        except SQLAlchemyError:
            db.session.rollback()
            message = 'Failed to add the book to the database.'

        # Update the list of books after adding a new book
        books = Book.query.order_by(Book.title.asc()).all()
        return render_template('home.html', books=books, message=message)

    authors = db.session.query(Author).order_by(Author.name.asc()).all()
    return render_template('add_book.html', authors=authors, message=message)


@app.route('/book/<int:book_id>/delete')
def delete_book(book_id):
    try:
        book_to_delete = Book.query.get(book_id)

        if book_to_delete:
            Book.query.filter(Book.id == book_id).delete()
            db.session.commit()
            message = f'Book {book_id} has been deleted from the database.'
        else:
            message = f'Book {book_id} not found.'

    except SQLAlchemyError:
        db.session.rollback()
        message = f'Failed to delete book {book_id}.'

    books = Book.query.order_by(Book.title.asc()).all()
    return render_template('home.html', books=books, message=message)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
