import streamlit as st
from db import db, app, User, Movie, Rating
from surprise import Dataset, Reader, SVD
import pandas as pd
from datetime import datetime
import random
from neo4j_utils import get_explanation, add_rating, add_user



st.set_page_config(page_title="Movie Recommender", layout="wide")
st.title("🎬 Movie Recommender System")
popular_movie = [{"movie_title": "Titanic (1997)", "explanations": [{'type': 'Fall Back Explantion','explanation': "Recommended based on popularity."}]}, 
                 {"movie_title": "E.T. the Extra-Terrestrial (1982)", "explanations": [{'type': 'Fall Back Explantion','explanation': "Recommended based on popularity."}]},
                 {"movie_title": "The Wizard of Oz (1939)", "explanations": [{'type': 'Fall Back Explantion','explanation': "Recommended based on popularity."}]},
                 {"movie_title": "Star Wars: Episode IV - A New Hope (1977)", "explanations": [{'type': 'Fall Back Explantion','explanation': "Recommended based on popularity."}]},
                 {"movie_title": "The Lord of the Rings: The Return of the King (2003)", "explanations": [{'type': 'Fall Back Explantion','explanation': "Recommended based on popularity."}]}
                ]

# -----------------------
# Helpers
# -----------------------
def login_user(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
            add_user(user.id, username)
        return user.id

def fetch_selected_movies(limit=5):
    with app.app_context():
        movies = Movie.query.all()
        return random.sample(movies, k=min(limit, len(movies)))
    
def fetch_all_movies():
    with app.app_context():
        return Movie.query.all()
    
def get_rated_movies_number():
    with app.app_context():
        rated = {r.movie_id for r in Rating.query.filter_by(user_id=st.session_state.user_id).all()}
        return len(rated)
    
def fetch_rated_movies_with_ratings():
    with app.app_context():
        rated = {r.movie_id: r.rating for r in Rating.query.filter_by(user_id=st.session_state.user_id).all()}
        all_movies = {m.id: m for m in Movie.query.all()}
        rated_movies = [(m, rated[m.id]) for m in all_movies.values() if m.id in rated]
        return rated_movies
    
def get_rated_movies_with_ratings_as_df():
    with app.app_context():
        rated = {r.movie_id: r.rating for r in Rating.query.filter_by(user_id=st.session_state.user_id).all()}
        all_movies = {m.id: m for m in Movie.query.all()}
        rated_movies = [(m.title, rated[m.id]) for m in all_movies.values() if m.id in rated]
        df = pd.DataFrame(rated_movies, columns=["Movie", "Rating"])
        return df

def submit_rating(user_id, movie_id, rating):
    with app.app_context():
        existing = Rating.query.filter_by(user_id=user_id, movie_id=movie_id).first()
        if existing:
            existing.rating = rating
        else:
            r = Rating(user_id=user_id, movie_id=movie_id, rating=rating)
            db.session.add(r)
        add_rating(user_id, movie_id, rating)
        db.session.commit()
        if "need_retrain" in st.session_state:
            st.session_state.need_retrain = True
        
def train_model():
    with app.app_context():
        ratings = Rating.query.all()
        if not ratings:
            return []
        data = [(str(r.user_id), str(r.movie_id), r.rating) for r in ratings]
        df = pd.DataFrame(data, columns=["userID", "itemID", "rating"])
        reader = Reader(rating_scale=(1.0, 5.0))
        trainset = Dataset.load_from_df(df, reader).build_full_trainset()
        model = SVD()
        model.fit(trainset)
        return model
    
def  get_recommendations_with_trained_model(model, user_id, n=5):
         with app.app_context():

            all_movies = {str(m.id): m for m in Movie.query.all()}
            rated = {str(r.movie_id) for r in Rating.query.filter_by(user_id=user_id).all()}
            unseen = set(all_movies.keys()) - rated

            predictions = [(mid, model.predict(str(user_id), mid).est) for mid in unseen]
            # Filter for predictions with rating >= 4.0
            high_rated = [(mid, score) for mid, score in predictions if score >= 4.0]

            # Randomly select n from high-rated movies
            top_n = random.sample(high_rated, min(n, len(high_rated)))

            return [{"movie_title": all_movies[mid].title, "explanations": get_explanation(user_id,mid), "score": round(score,1)} for mid, score in top_n]

def get_recommendations_with_explanation(user_id, n=5):
    try:
        with app.app_context():
            ratings = Rating.query.all()
            if not ratings:
                return []

            data = [(str(r.user_id), str(r.movie_id), r.rating) for r in ratings]
            df = pd.DataFrame(data, columns=["userID", "itemID", "rating"])

            reader = Reader(rating_scale=(1.0, 5.0))
            trainset = Dataset.load_from_df(df, reader).build_full_trainset()

            model = SVD()
            model.fit(trainset)

            all_movies = {str(m.id): m for m in Movie.query.all()}
            rated = {str(r.movie_id) for r in Rating.query.filter_by(user_id=user_id).all()}
            unseen = set(all_movies.keys()) - rated

            predictions = [(mid, model.predict(str(user_id), mid).est) for mid in unseen]
            top_n = sorted(predictions, key=lambda x: x[1], reverse=True)[:n]

        return [{"movie_title": all_movies[mid].title, "explanations": get_explanation(user_id,mid), "score": round(score,1)} for mid, score in top_n]

    except Exception as e:

        return None


# -----------------------
# Streamlit Interface
# -----------------------
if "model" not in st.session_state:
    st.session_state.model = train_model()
if "need_retrain" not in st.session_state:
    st.session_state.need_retrain = False
# 1. User login
username = st.text_input("Enter your username:")
if st.button("Login") and username:
    user_id = login_user(username)
    st.session_state.user_id = user_id
    st.success(f"Logged in as {username} (User ID: {user_id})")

# 2. Rating section
if "user_id" in st.session_state:
    movies = fetch_all_movies()

    col1, col2 = st.columns([0.3,0.7])
        
    with col1:
        st.header("🎬 Rate Movies")
        if "selected_movie" not in st.session_state:
            st.session_state.selected_movie = random.choice(movies)
        if "selected_movie_rating" not in st.session_state:
            st.session_state.selected_movie_rating = 1
        if "random_index" not in st.session_state:
            st.session_state.random_index = random.randint(0, len(movies) - 1)
        @st.fragment
        def create_selected_movie(movies):
            if st.button("Get New Random Movie", key="generate_new_selected_movie"):
                st.session_state.random_index = random.randint(0, len(movies) - 1)
                
            st.session_state.selected_movie = st.selectbox("Select movies:", movies, st.session_state.random_index, format_func=lambda x: x.title, key="movie_select_random", label_visibility="collapsed")
        create_selected_movie(movies)
        
        @st.fragment
        def submit_rating_random():
            st.session_state.selected_movie_rating = st.feedback("stars", key="rating_feedback_radom")
           
        submit_rating_random()
        if st.button(f"Submit Rating", key=f"submit_rating_random"):
            submit_rating(st.session_state.user_id, st.session_state.selected_movie.id, st.session_state.selected_movie_rating + 1)
            st.success(f"Rated {st.session_state.selected_movie.title} with {st.session_state.selected_movie_rating + 1} ⭐")
            
        st.header("✅ Rated Movies")
        st.dataframe(
            get_rated_movies_with_ratings_as_df(),
            column_config={
                "Movie": "Movie",
                "Rating": st.column_config.NumberColumn(
                    "Rating",
                    format="%d ⭐",
                ),
            })

    with col2:
        st.header("📺 Recommended Movies")
        st.write("Please rate at least 20 movies to get accurate recommendations.")
        
        if st.button("📌 Get Recommendations"):
            rated_movies_number = get_rated_movies_number()
            if st.session_state.need_retrain:
                st.session_state.model = train_model()
                st.session_state.need_retrain = False
            recs = get_recommendations_with_trained_model(st.session_state.model,st.session_state.user_id)
            print(recs,flush=True)
            if rated_movies_number == 0 or len(recs) == 0:
                recs = popular_movie
            for r in recs:
                st.markdown(f"**{r['movie_title']}**")
                for explanation in r['explanations']:
                    st.caption(f"{explanation['type']}: {explanation['explanation']}")

