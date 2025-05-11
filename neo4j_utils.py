from neo4j import GraphDatabase

# Replace these with your Neo4j DB credentials
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def explain_by_genre(user_id, movie_id):
    query = """
        MATCH (u:User {id: $user_id})-[:RATED]->(m:Movie)-[:HAS_GENRE]->(g:Genre),
            (target:Movie {id: $movie_id})-[:HAS_GENRE]->(g)
        WITH g, COUNT(*) AS count
        ORDER BY count DESC
        LIMIT 3
        RETURN collect(g.name) AS top_genres
    """
    with driver.session() as session:
        result = session.run(query, user_id=int(user_id), movie_id=int(movie_id))
        print(result)
        record = result.single()
        if record and record["top_genres"]:
            genre_list = record["top_genres"]
            if len(genre_list) == 1:
                genre_str = genre_list[0]
            elif len(genre_list) == 2:
                genre_str = " and ".join(genre_list)
            else:
                genre_str = ", ".join(genre_list[:-1]) + ", and " + genre_list[-1]
            return f"You might like this movie because you often watch {genre_str} movies."
        return None
    
def explain_by_shared_genres(user_id, movie_id):
    query = """
        MATCH (u:User {id: $user_id})-[r:RATED]->(watched:Movie)
        WHERE r.score >= 4.0
        MATCH (watched)-[:HAS_GENRE]->(g:Genre),
              (target:Movie {id: $movie_id})-[:HAS_GENRE]->(g)
        WITH watched, COUNT(g) AS shared_genre_count
        ORDER BY shared_genre_count DESC
        RETURN watched.title AS rated_movie, shared_genre_count
        LIMIT 3
    """
    with driver.session() as session:
        result = session.run(query, user_id=int(user_id), movie_id=int(movie_id))
        record = result.data()
        print(record)
        if record:
            # return f"You might like this movie because it shares {record['shared_genre_count']} genres with '{record['rated_movie']}', which you watched."
            rated_movies = ','.join([r['rated_movie'] for r in record])
            return f"You might like this movie because you enjoyed similar movies: {rated_movies}."
        return None
    
def explain_by_similar_user(user_id, movie_id):
    query = """
        MATCH (u1:User {id: $user_id})-[r1:RATED]->(m:Movie)
        MATCH (u2:User)-[r2:RATED]->(m)
        WHERE u1 <> u2
        AND ((r1.score >= 4.0 and r2.score >= 4.0) 
        OR (r1.score <= 3.0 AND r2.score <= 3.0))
        MATCH (u2)-[r3:RATED]->(target:Movie {id: $movie_id})
        WHERE r3.score >= 4.0
        WITH u2, COUNT(m) AS shared_count, r3.score AS score
        ORDER BY shared_count DESC
        RETURN u2.name AS similar_user, shared_count, score
        LIMIT 1
    """
    with driver.session() as session:
        result = session.run(query, user_id=int(user_id), movie_id=int(movie_id))
        record = result.single()
        if record:
            return (
                f"User {record['similar_user']} who has similar taste "
                f"(based on {record['shared_count']} movies) rated this movie {record['score']} stars."
            )
        return None

def get_explanation(user_id, movie_id):
    explanations = []
    try:
        explanation = explain_by_similar_user(user_id, movie_id)
        if explanation:
            explanations.append({'type': 'User-Based Explantion', 'explanation': explanation})

        explanation = explain_by_shared_genres(user_id, movie_id)
        if explanation:
            explanations.append({'type': 'Item-Based Explantion', 'explanation': explanation})

        explanation = explain_by_genre(user_id, movie_id)
        if explanation:
            explanations.append({'type': 'Genre-Based Explantion', 'explanation': explanation})

        if len(explanations) > 0:
            return explanations
        return [{'type': 'Fall Back Explantion','explanation': "Recommended based on your rating history."}]
    
    except Exception as e:
        return [{'type': 'Fall Back Explantion','explanation': "Recommended based on your rating history."}]
    

def add_rating(user_id, movie_id, rating):
    query = """
        MATCH (u:User {id: $user_id})
        MATCH (m:Movie {id: $movie_id})
        MERGE (u)-[r:RATED]->(m)
        SET r.score = $rating
    """
    with driver.session() as session:
        session.run(query, user_id=int(user_id), movie_id=int(movie_id), rating=float(rating))
        print(f"Added rating {rating} for movie {movie_id} by user {user_id}.")
        
def add_user(user_id, user_name):
    query = """
        CREATE (u:User {id: $user_id, name: $user_name})
    """
    with driver.session() as session:
        session.run(query, user_id=int(user_id), user_name=user_name)
        print(f"Added user {user_name} with ID {user_id}.")