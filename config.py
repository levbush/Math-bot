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

lang = "en"

repo_id = 'levbush/math_tasks_split'
repo_type = 'dataset'

FILE_LENGTH = 1000

REFRESH_INTERVAL = 15 * 60
CACHE_FILE = 'pool_cache.pkl'


def _default_stats() -> dict[str, int]:
    return {key: 0 for key in SUBJECTS + [str(d) for d in range(1, 11)]}


AI_COOLDOWN = 15