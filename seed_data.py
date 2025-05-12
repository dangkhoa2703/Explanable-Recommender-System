import pandas as pd
from db import db, app, User, Movie, Rating, Genre
from neo4j import GraphDatabase
import os

# Neo4j connection setup
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with app.app_context():
    # Seed users
    ratings_df = pd.read_csv("data/ratings.csv")
    user_ids = ratings_df["userId"].unique()
    for uid in user_ids:
        user = User(id=int(uid), username=f"user{uid}")
        db.session.merge(user)
    db.session.commit()

    # Load movie and link data
    movies_df = pd.read_csv("data/movies.csv")
    links_df = pd.read_csv("data/links.csv")
    movies_full = pd.merge(movies_df, links_df, on="movieId", how="left")

    # Prepare genre cache to prevent duplicates
    genre_cache = {}

    for _, row in movies_full.iterrows():
        genre_names = row["genres"].split("|") if row["genres"] and row["genres"] != "(no genres listed)" else []
        genre_objs = []

        for gname in genre_names:
            gname = gname.strip()
            if gname not in genre_cache:
                genre = Genre.query.filter_by(name=gname).first()
                if not genre:
                    genre = Genre(name=gname)
                    db.session.add(genre)
                    db.session.flush()  # ensure ID is assigned
                genre_cache[gname] = genre
            genre_objs.append(genre_cache[gname])

        movie = Movie(
            id=int(row["movieId"]),
            title=row["title"],
            imdb_id=str(row["imdbId"]) if not pd.isna(row["imdbId"]) else None,
            tmdb_id=str(row["tmdbId"]) if not pd.isna(row["tmdbId"]) else None
            )
        db.session.add(movie)

        # Safely assign genres now that movie is in the session
        with db.session.no_autoflush:
            movie.genres.extend(genre_objs)

    db.session.commit()
    
    # Seed ratings with optional tags
    for _, row in ratings_df.iterrows():
        uid, mid = int(row["userId"]), int(row["movieId"])

        rating = Rating(
            user_id=uid,
            movie_id=mid,
            rating=float(row["rating"])
        )
        db.session.add(rating)
    db.session.commit()

    print("✅ Database seeded successfully.", flush=True)
    
    # 👉 Neo4j population
    print("🌐 Populating Neo4j...", flush=True)
    
    
    print("🚀 Bulk inserting into Neo4j with CREATE...", flush=True)

    with driver.session() as neo_session:
        # 1. Create Users
        users = User.query.all()
        for user in users:
            neo_session.run(
                "CREATE (:User {id: $id, name: $name})",
                id=user.id, name=user.username
            )

        # 2. Create Movies
        movies = Movie.query.all()
        for movie in movies:
            neo_session.run(
                "CREATE (:Movie {id: $id, title: $title})",
                id=movie.id, title=movie.title
            )

        # 3. Create Genres
        genres = Genre.query.all()
        for genre in genres:
            neo_session.run(
                "CREATE (:Genre {name: $name})",
                name=genre.name
            )

        # 4. Create HAS_GENRE relationships
        for movie in movies:
            for genre in movie.genres:
                neo_session.run("""
                    MATCH (m:Movie {id: $movie_id}), (g:Genre {name: $genre_name})
                    CREATE (m)-[:HAS_GENRE]->(g)
                """, movie_id=movie.id, genre_name=genre.name)

        # 5. Create RATED relationships
        ratings = Rating.query.all()
        for rating in ratings:
            neo_session.run("""
                MATCH (u:User {id: $user_id}), (m:Movie {id: $movie_id})
                CREATE (u)-[:RATED {score: $score}]->(m)
            """, user_id=rating.user_id, movie_id=rating.movie_id, score=rating.rating)

    driver.close()
    print("✅ Fast Neo4j import complete.", flush=True)


    



