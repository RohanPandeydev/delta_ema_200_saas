from app import create_app, db
from app.models.user import User
from app.models.bot import BotConfiguration

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    print("Database tables created successfully!")
    
    # Optional: Create a test user
    try:
        test_user = User(
            username='testuser',
            email='test@example.com',
            is_premium=True
        )
        test_user.set_password('testpassword')
        db.session.add(test_user)
        db.session.commit()
        print("Test user created: testuser / testpassword")
    except:
        db.session.rollback()
        print("Test user already exists or error occurred")