import json
import pickle
import random
import threading
import time
import tempfile
import os
import shutil
from huggingface_hub import hf_hub_download, list_repo_files
from config import SUBJECTS, repo_id, repo_type, REFRESH_INTERVAL, CACHE_FILE

_lock = threading.Lock()
_pool: dict[tuple, list] = {}
_tmp_dir = tempfile.mkdtemp(prefix='mather_cache_')

BLACKLIST = ['an educational piece', '¶', "Here's an extract", 'Welsh teams']

MAX_PROBLEMS_PER_KEY = 1000


def _is_valid(question: str) -> bool:
    return not any(phrase in question for phrase in BLACKLIST)


def _translate_problem(problem: dict) -> dict:
    try:
        from data.ai import translate_text
        
        original_question = problem['question']
        translated_question = translate_text(original_question)
        
        translated_problem = problem.copy()
        translated_problem['question'] = translated_question
        translated_problem['original_question'] = original_question
        
        return translated_problem
    except Exception:
        return problem


def _load_file(filepath: str, exclude_ids: set) -> list:
    problems = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                p = json.loads(line)
                if p['id'] not in exclude_ids and _is_valid(p['question']):
                    problems.append(p)
            except json.JSONDecodeError:
                continue
    return problems


def _cleanup_temp_dir():
    try:
        if os.path.exists(_tmp_dir):
            for filename in os.listdir(_tmp_dir):
                filepath = os.path.join(_tmp_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath)
    except Exception:
        pass


def _download_for(subject: str, difficulty: str) -> list:
    subdir = f'{subject}/{difficulty}/' if difficulty != 'any' else f'{subject}/'

    try:
        all_files = list_repo_files(repo_id, repo_type=repo_type)
    except Exception:
        return []

    files = [
        f for f in all_files
        if f.startswith(subdir)
        and not f.endswith('/')
        and not f.endswith('whole.jsonl')
    ]

    if not files:
        return []

    random.shuffle(files)

    collected = []
    seen_ids = set()

    for file in files:
        if len(collected) >= MAX_PROBLEMS_PER_KEY:
            break

        try:
            local_path = hf_hub_download(
                repo_id=repo_id,
                filename=file,
                repo_type=repo_type,
                local_dir=_tmp_dir
            )

            problems = _load_file(local_path, seen_ids)

            for p in problems:
                if len(collected) >= MAX_PROBLEMS_PER_KEY:
                    break
                collected.append(p)
                seen_ids.add(p['id'])

        except Exception:
            continue

    return collected


def _save_pool(pool: dict):
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(pool, f)
    except Exception:
        pass


def _load_pool() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'rb') as f:
            pool = pickle.load(f)
        return pool
    except Exception:
        return {}


def _refresh():
    _cleanup_temp_dir()
    
    new_pool = {}

    for subject in SUBJECTS:
        for difficulty in [str(d) for d in range(1, 11)]:
            key = (subject, difficulty)
            problems = _download_for(subject, difficulty)
            new_pool[key] = problems

    with _lock:
        _pool.clear()
        _pool.update(new_pool)

    _save_pool(new_pool)


def _background_loop():
    while True:
        try:
            _refresh()
        except Exception:
            pass
        time.sleep(REFRESH_INTERVAL)


def start():
    saved = _load_pool()
    
    if saved:
        with _lock:
            _pool.update(saved)
        threading.Thread(target=_background_loop, daemon=True).start()
    else:
        def first_refresh():
            time.sleep(1)
            _refresh()
            _background_loop()
        
        threading.Thread(target=first_refresh, daemon=True).start()


def get_problem(subject: str, difficulty: str, solved_ids: set, lang: str) -> dict | None:
    with _lock:
        if difficulty == 'any':
            candidates = [
                p
                for (s, _), problems in _pool.items()
                if s == subject
                for p in problems
            ]
        else:
            candidates = list(_pool.get((subject, difficulty), []))

    unsolved = [p for p in candidates if p['id'] not in solved_ids]

    if not unsolved:
        return None

    problem = random.choice(unsolved)
    
    if lang == 'ru' and 'original_question' not in problem:
        problem = _translate_problem(problem)
        
    return problem
