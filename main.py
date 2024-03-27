from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from dotenv import load_dotenv
import os
import requests

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

# API CONNECTION
SEARCH_API_URL = "https://api.themoviedb.org/3/search/movie"
INFO_API_URL = "https://api.themoviedb.org/3/movie/"
IMG_API_URL = "https://image.tmdb.org/t/p/w500"

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {TMDB_TOKEN}",
}


app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
Bootstrap5(app)


# CREATE DB
class Base(DeclarativeBase):
    pass


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies.db"
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CREATE TABLE
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String[250], unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String[500], nullable=False)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    review: Mapped[str] = mapped_column(String[250], nullable=True)
    img_url: Mapped[str] = mapped_column(String[250], nullable=False)


with app.app_context():
    db.create_all()


# CREATE FORMS
class EditForm(FlaskForm):
    rating = StringField(
        label="Your Rating Out of 10 e.g. 7.5", validators=[DataRequired()]
    )
    review = StringField(label="Your Review", validators=[DataRequired()])
    submit = SubmitField(
        label="Done",
    )


class AddForm(FlaskForm):
    title = StringField(label="Movie Title", validators=[DataRequired()])
    submit = SubmitField(label="Add Movie")


@app.route("/")
def home():
    result = db.session.execute(db.select(Movie).order_by(Movie.rating))
    all_movies = result.scalars().all()
    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i
    db.session.commit()

    return render_template("index.html", movies=all_movies)


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    add_form = AddForm()
    if add_form.validate_on_submit():
        title = add_form.title.data
        params = {
            "query": title,
            "include_adult": False,
            "language": "en-US",
            "page": 1,
        }
        response = requests.get(SEARCH_API_URL, params=params, headers=HEADERS)
        response.raise_for_status()
        data = response.json()["results"]
        return render_template("select.html", movies=data)
    return render_template("add.html", form=add_form)


@app.route("/find")
def find_movie():
    movie_api_id = request.args.get("id")
    if movie_api_id:
        movie_api_url = f"{INFO_API_URL}{movie_api_id}"
        params = {"language": "en-US"}
        response = requests.get(movie_api_url, params=params, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        new_movie = Movie(
            title=data["title"],
            year=data["release_date"].split("-")[0],
            img_url=f"{IMG_API_URL}{data['poster_path']}",
            description=data["overview"],
        )
        print(new_movie.img_url)
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("edit_movie", id=new_movie.id))


@app.route("/edit", methods=["GET", "POST"])
def edit_movie():
    edit_form = EditForm()
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    if edit_form.validate_on_submit():
        movie.rating = float(edit_form.rating.data)
        movie.review = edit_form.review.data
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("edit.html", movie=movie, form=edit_form)


@app.route("/delete")
def delete_movie():
    movie_id = request.args.get("id")
    movie_to_delete = db.get_or_404(Movie, movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run()
