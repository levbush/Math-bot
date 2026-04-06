import dotenv


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

ACHIEVEMENTS = [
    "10 tasks in a row without errors",
    "100 solved tasks",
    "topic completion"
]

lang = "ru"

repo_id = 'levbush/math_tasks_split'
repo_type = 'dataset'

FILE_LENGTH = 1000

REFRESH_INTERVAL = 15 * 60
CACHE_FILE = 'pool_cache.pkl'
