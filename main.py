from data.db_session import global_init
from data.cache import start as start_cache
from logic.app import app
from logic.login import login_manager
from config import DB_PATH

AI_COOLDOWN = 15

global_init(DB_PATH)
start_cache()

def main():
    app.run(port=8080, host='127.0.0.1')


if __name__ == '__main__':
    main()
