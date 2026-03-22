import random, json, os
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
import aiogram.types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from db import get_stats, get_data, save_data
from helpers import latex_to_text, stats_to_text
from huggingface_hub import list_repo_files, hf_hub_download
from uuid import uuid4
from config import SUBJECTS, repo_id, repo_type


router = Router()


@router.message(Command('start'))
async def start(message: types.Message):
    await message.answer(
        'Hello! It\'s a bot that allows you to solve variety of mathematical problems of different levels. Type /help to learn about different commands. Remember about /cancel as well.'
    )


@router.message(Command('help'))
async def help_cmd(message: types.Message):
    await message.answer(
        '''/find_problem - find a problem.
/more - find a problem within the same subject and difficulty.
/stats - show your solving stats.
/cancel - very important command, use it when you don't want to press a button or answer.'''
    )


@router.inline_query()
async def inline_handler(inline_query: aiogram.types.InlineQuery):
    user_id = inline_query.from_user.id

    results = []

    text = 'My stats:\n' + stats_to_text(get_stats(user_id))

    results.append(
        aiogram.types.InlineQueryResultArticle(
            id=str(uuid4()),
            title='Your stats',
            input_message_content=aiogram.types.InputTextMessageContent(message_text=text),
        )
    )

    await inline_query.answer(results, cache_time=1)


@router.message(Command('stats'))
async def help_cmd(message: types.Message):
    await message.answer('Your stats:\n' + stats_to_text(get_stats(message.from_user.id)))


class States(StatesGroup):
    on_choosing_subject = State()
    on_choosing_difficulty = State()


@router.message(Command('find_problem'))
async def find_problem(message: types.Message, state: FSMContext):
    await message.answer(f'Choose a subject from {', '.join(SUBJECTS)}:')
    await state.set_state(States.on_choosing_subject)


@router.message(States.on_choosing_subject)
async def choose_subject(message: types.Message, state: FSMContext):
    if message.text.strip().capitalize() not in SUBJECTS:
        await message.answer(f'Choose a subject from {', '.join(SUBJECTS)}')
        return
    await state.clear()
    await state.set_state(States.on_choosing_difficulty)
    await state.set_data({'subject': message.text.strip().capitalize()})
    await message.answer('Choose a difficulty from 1 to 10 or "any":')


def receive_problem(subject: str, difficulty: str, uid: int):
    subdir_name = f'{subject}/{difficulty}/' if difficulty != 'any' else subject + '/'
    all_files = list_repo_files(repo_id, repo_type=repo_type)
    solved_problems = get_data(uid).solved

    files = [f for f in all_files if f.startswith(subdir_name) and not f.endswith('/')]
    files = [f for f in files if not f.endswith('whole.jsonl')]
    attempts = 0
    max_attempts = 20

    random.shuffle(files)

    for file in files:
        if attempts >= max_attempts:
            break

        local_path = hf_hub_download(repo_id=repo_id, filename=file, repo_type=repo_type)

        try:
            unsolved_in_file = []
            with open(local_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f):
                    if attempts >= max_attempts:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    try:
                        problem = json.loads(line)

                        if problem['id'] not in solved_problems:
                            unsolved_in_file.append(problem)
                            attempts += 1

                    except json.JSONDecodeError as e:
                        print(f'Error parsing JSON in {file}, line {line_num}: {e}')
                        continue

            if unsolved_in_file:
                problem = random.choice(unsolved_in_file)
                break

        finally:
            try:
                os.remove(local_path)
            except OSError as e:
                print(f'Error deleting file {local_path}: {e}')
    return problem


@router.message(States.on_choosing_difficulty)
async def choose_difficulty_and_receive_problem(message: types.Message, state: FSMContext):
    if message.text.strip().lower() != 'any' and (
        not message.text.strip().isdigit() or int(message.text.strip()) not in range(10)
    ):
        await message.answer('Choose a difficulty from 1 to 10 or "any"')
        return

    user_data = await state.get_data()
    subject = user_data['subject']
    difficulty = message.text.strip()

    uid = message.from_user.id

    await state.clear()
    await state.update_data({'difficulty': difficulty.lower()})

    problem = receive_problem(subject, difficulty, uid)

    if not problem:
        await message.answer('You seem to have solved all the tasks in the file. Try again in a few seconds.')
        return

    await state.update_data(problem)

    await message.answer(f'📝 Problem (Difficulty: {problem["difficulty"]}):\n\n{latex_to_text(problem["question"])}\n\nFormat: {problem["format"]}', reply_markup=aiogram.types.InlineKeyboardMarkup(inline_keyboard=[[aiogram.types.InlineKeyboardButton(text='Check answer', callback_data='solved:check_answer')]]))


@router.callback_query(F.data == 'solved:check_answer')
async def check_answer(call: aiogram.types.CallbackQuery, state: FSMContext, bot: aiogram.Bot):
    problem = await state.get_data()
    await bot.send_message(call.from_user.id, f'''Solution:
{latex_to_text(problem['response'])}

{'Extracted answer: ' + latex_to_text(problem['extracted_answer']) if problem['extracted_answer'] else ''}''', reply_markup=aiogram.types.InlineKeyboardMarkup(inline_keyboard=[[aiogram.types.InlineKeyboardButton(text='My answer is correct (type /cancel instead)', callback_data='solved:confirm_answer')]]))


@router.callback_query(F.data == 'solved:confirm_answer')
async def confirm_answer(call: aiogram.types.CallbackQuery, state: FSMContext, bot: aiogram.Bot):
    problem = await state.get_data()
    data = get_data(call.from_user.id)
    data.solved.add(problem['id'])
    data.stats[problem['subject']] += 1
    data.stats[str(problem['difficulty'])] += 1
    save_data(call.from_user.id, data)
    await bot.send_message(call.from_user.id, 'Task marked as solved')

@router.message(Command('more'))
async def more(message: types.Message, state: FSMContext):
    prev_problem = await state.get_data()
    
    problem = receive_problem(prev_problem['subject'], prev_problem['difficulty'], message.from_user.id)

    if not problem:
        await message.answer('You seem to have solved all the tasks in the file. Try again in a few seconds.')
        return

    await state.update_data(problem)

    await message.answer(f'📝 Problem (Difficulty: {problem['difficulty']}):\n\n{latex_to_text(problem['question'])}\n\nFormat: {problem['format']}', reply_markup=aiogram.types.InlineKeyboardMarkup(inline_keyboard=[[aiogram.types.InlineKeyboardButton(text='Check answer', callback_data='solved:check_answer')]]))


@router.message(Command('cancel'), StateFilter('*'))
async def cancel_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer('Cancelled')