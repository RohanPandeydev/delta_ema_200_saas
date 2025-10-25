from app import db

# Import all models here
from app.models.user import User
from app.models.bot import BotConfiguration

__all__ = ['User', 'BotConfiguration']