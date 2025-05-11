from db import db, User, Rating, app

with app.app_context():
    # First delete ratings associated with users >= 611
    ratings_to_delete = Rating.query.filter(Rating.user_id >= 611).all()
    for rating in ratings_to_delete:
        db.session.delete(rating)

    # Then delete the users themselves
    users_to_delete = User.query.filter(User.id >= 611).all()
    for user in users_to_delete:
        db.session.delete(user)

    db.session.commit()

print("✅ Users with id >= 611 and their ratings deleted from RDBMS.")
