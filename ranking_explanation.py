# Ranking explanation
def get_explanation(user_id, movie_id):
    try:
        explanation = explain_by_similar_user(user_id, movie_id)
        if explanation:
            return explanation

        explanation = explain_by_shared_genres(user_id, movie_id)
        if explanation:
            return explanation

        explanation = explain_by_genre(user_id, movie_id)
        if explanation:
            return explanation

        return "Recommended based on your rating history."
    except Exception as e:
        return "Recommended based on your rating history."
