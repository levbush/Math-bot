import dotenv
from eng_to_ru import Translator


translator = Translator()

dotenv.load_dotenv()

DB_PATH = 'bot.db'

SUBJECTS = [
    'Arithmetic',
    'Algebra',
    'Pre-Algebra',
    'Geometry',
    'Probability & Statistics',
    'Combinatorics',
    'Number Theory',
    'Logic & Discrete Math',
    'Linear Algebra',
    'Trigonometry',
    'Calculus',
    'Other'
]

lang = "ru"

repo_id = 'levbush/math_tasks_split'
repo_type = 'dataset'

FILE_LENGTH = 1000

REFRESH_INTERVAL = 15 * 60
CACHE_FILE = 'pool_cache.pkl'
