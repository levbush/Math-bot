import sqlite3
import pickle
from config import DB_PATH, DEFAULT_DATA, Data
# from cachetools import TTLCache


def get_conn(row_factory=False):
    conn = sqlite3.connect(DB_PATH)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def init_dbs():
    conn = get_conn()
    c = conn.cursor()

    c.execute(
        '''CREATE TABLE IF NOT EXISTS user_data (
            uid PRIMARY KEY,
            data BINARY
    )'''
    )

    conn.commit()
    conn.close()


def get_data(uid: int) -> Data:
    conn = get_conn()
    c = conn.cursor()
    data = c.execute('SELECT data from user_data WHERE uid = ?', (uid,)).fetchone()
    if data is None:
        return DEFAULT_DATA
    data = data[0]
    data = pickle.loads(data)
    if not isinstance(data, Data):
        return DEFAULT_DATA
    return data


def save_data(uid: int, data: Data):
    conn = get_conn()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO user_data VALUES (?, ?)', (uid, pickle.dumps(data)))
    conn.commit()
    conn.close()


def get_stats(uid: int):
    return get_data(uid).stats
