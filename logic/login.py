from flask_login import LoginManager
from .app import app
from data.user import User

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))
