from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import os
from datetime import datetime

API_TOKEN = "8340476999:AAHvwY4YBn6YHkHwRHq0HCYHG82Gq5yPECo"
ADMIN_ID = 1475331727

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

seekers = {}
employers = {}
pending_vacancies = []

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Ищу работу")],
        [KeyboardButton(text="Ищу сотрудника")],
        [KeyboardButton(text="Мой профиль")],
        [KeyboardButton(text="Отписаться от вакансий")]
    ], resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Ищу работу")],
        [KeyboardButton(text="Ищу сотрудника")],
        [KeyboardButton(text="Мой профиль")],
        [KeyboardButton(text="Отписаться от вакансий")],
        [KeyboardButton(text="🛠 Модерация")],
        [KeyboardButton(text="📊 Аналитика")]
    ], resize_keyboard=True
)

specialties = ["Backend Developer", "Frontend Developer", "DevOps Engineer", "QA Engineer", "Analytics", "Product Manager", "Designer"]

def nav_keyboard(buttons_list):
    kb = buttons_list + [[KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="🏠 Главное меню")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

levels = ["Junior", "Middle", "Senior"]
cities = ["Алматы", "Астана", "Шымкент", "Караганда", "Актобе"]
work_formats = ["Офис", "Удаленка", "Гибрид"]

class SeekerStates(StatesGroup):
    choosing_specialty = State()
    choosing_level = State()
    choosing_salary = State()
    uploading_cv = State()

class EmployerStates(StatesGroup):
    choosing_position = State()
    typing_description = State()
    choosing_level = State()
    typing_salary = State()
    choosing_city = State()
    choosing_format = State()
    typing_link = State()

@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Добро пожаловать, админ!", reply_markup=admin_menu)
    else:
        await message.answer("Добро пожаловать!", reply_markup=main_menu)
@dp.message(F.text == "🛠 Модерация")
async def admin_moderation(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен.")
        return
    if not pending_vacancies:
        await message.answer("Нет вакансий на модерацию.")
        return
    text = ""
    for idx, vac in enumerate(pending_vacancies, start=1):
        text += f"{idx}. {vac['position']} | {vac['level']} | {vac['city']}\n"
    await message.answer(f"Список вакансий на модерацию:\n{text}")

@dp.message(F.text == "📊 Аналитика")
async def admin_analytics(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен.")
        return
    total_seekers = len(seekers)
    total_employers = len(employers)
    total_vacancies = sum(len(emp.get("active_vacancies", [])) for emp in employers.values())
    await message.answer(f"📊 Статистика:\nСоискатели: {total_seekers}\nРаботодатели: {total_employers}\nВакансий: {total_vacancies}")
@dp.message(F.text == "Мой профиль")
async def my_profile(message: types.Message):
    user_id = message.from_user.id

    profile_text = f"👤 Ваш профиль:\n\n"
    profile_text += f"Имя: {message.from_user.full_name}\n"
    profile_text += f"Username: @{message.from_user.username if message.from_user.username else 'нет'}\n"

    if user_id in employers:
        vacancies = employers[user_id].get("active_vacancies", [])
        profile_text += f"Размещённые вакансии: {len(vacancies)}\n"
    else:
        profile_text += "Размещённые вакансии: 0\n"

    cv_folder = "cv_files"
    user_cvs = []
    if os.path.exists(cv_folder):
        for f in os.listdir(cv_folder):
            if f.startswith(str(user_id)):
                user_cvs.append(f)
    profile_text += f"Загруженные CV: {len(user_cvs)}"

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ Назад")],
            [KeyboardButton(text="🏠 Главное меню")]
        ], resize_keyboard=True
    )

    await message.answer(profile_text, reply_markup=kb)
@dp.message(F.text == "Ищу работу")
async def find_job(message: types.Message, state: FSMContext):
    kb = nav_keyboard([[KeyboardButton(text=s)] for s in specialties])
    await message.answer("Выберите специальность:", reply_markup=kb)
    await state.set_state(SeekerStates.choosing_specialty)

@dp.message(SeekerStates.choosing_specialty, F.text.in_(specialties))
async def choose_specialty(message: types.Message, state: FSMContext):
    await state.update_data(specialty=message.text)
    kb = nav_keyboard([[KeyboardButton(text=l)] for l in levels])
    await message.answer("Выберите уровень опыта:", reply_markup=kb)
    await state.set_state(SeekerStates.choosing_level)

@dp.message(SeekerStates.choosing_level, F.text.in_(levels))
async def choose_level(message: types.Message, state: FSMContext):
    await state.update_data(level=message.text)
    await message.answer("Укажите желаемую зарплату в ₸:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(SeekerStates.choosing_salary)

@dp.message(SeekerStates.choosing_salary)
async def choose_salary(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число, например: 450000")
        return
    await state.update_data(salary=int(message.text))
    await message.answer("Отправьте ваше CV (PDF, JPG, PNG):")
    await state.set_state(SeekerStates.uploading_cv)

@dp.message(F.content_type.in_(["document", "photo"]))
async def upload_cv(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not os.path.exists("cv_files"):
        os.mkdir("cv_files")

    if message.document:
        ext = message.document.file_name.split('.')[-1]
        if ext.lower() not in ["pdf", "jpg", "png"]:
            await message.answer("Я могу принять только PDF, JPG или PNG. Попробуйте снова.")
            return
        file_path = f"cv_files/{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        file = await bot.get_file(message.document.file_id)
        await bot.download_file(file.file_path, destination=file_path)

    elif message.photo:
        file_path = f"cv_files/{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        file = await bot.get_file(message.photo[-1].file_id)
        await bot.download_file(file.file_path, destination=file_path)

    await message.answer("✅ CV загружено!", reply_markup=main_menu)
    await state.clear()



@dp.message(F.text == "Ищу сотрудника")
async def employer_start(message: types.Message, state: FSMContext):
    kb = nav_keyboard([[KeyboardButton(text="➕ Разместить вакансию")], [KeyboardButton(text="📋 Мои вакансии")]])
    await message.answer("Что вы хотите сделать?", reply_markup=kb)

@dp.message(F.text == "➕ Разместить вакансию")
async def post_vacancy_start(message: types.Message, state: FSMContext):
    kb = nav_keyboard([[KeyboardButton(text=s)] for s in specialties])
    await message.answer("Выберите должность:", reply_markup=kb)
    await state.set_state(EmployerStates.choosing_position)

@dp.message(EmployerStates.choosing_position, F.text.in_(specialties))
async def choose_position(message: types.Message, state: FSMContext):
    await state.update_data(position=message.text)
    await message.answer("Напишите описание вакансии:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EmployerStates.typing_description)

@dp.message(EmployerStates.typing_description)
async def type_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    kb = nav_keyboard([[KeyboardButton(text=l)] for l in levels])
    await message.answer("Выберите уровень опыта:", reply_markup=kb)
    await state.set_state(EmployerStates.choosing_level)

@dp.message(EmployerStates.choosing_level, F.text.in_(levels))
async def choose_emp_level(message: types.Message, state: FSMContext):
    await state.update_data(level=message.text)
    await message.answer("Укажите зарплату:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EmployerStates.typing_salary)

@dp.message(EmployerStates.typing_salary)
async def type_salary(message: types.Message, state: FSMContext):
    await state.update_data(salary=message.text)
    kb = nav_keyboard([[KeyboardButton(text=c)] for c in cities])
    await message.answer("Выберите город:", reply_markup=kb)
    await state.set_state(EmployerStates.choosing_city)

@dp.message(EmployerStates.choosing_city, F.text.in_(cities))
async def choose_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    kb = nav_keyboard([[KeyboardButton(text=f)] for f in work_formats])
    await message.answer("Выберите формат работы:", reply_markup=kb)
    await state.set_state(EmployerStates.choosing_format)

@dp.message(EmployerStates.choosing_format, F.text.in_(work_formats))
async def choose_format(message: types.Message, state: FSMContext):
    await state.update_data(work_format=message.text)
    await message.answer("Добавьте ссылку на вакансию или 'Нет':", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EmployerStates.typing_link)

@dp.message(EmployerStates.typing_link)
async def type_link(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text if message.text.lower() != "нет" else "")
    user_id = message.from_user.id
    contact = message.from_user.username
    data = await state.get_data()
    vacancy = {"position": data["position"], "description": data["description"], "level": data["level"], "salary": data["salary"], "city": data["city"], "work_format": data["work_format"], "link": data["link"], "contact": contact, "candidates": [], "status": "✅ Активна"}
    employers.setdefault(user_id, {"username": message.from_user.username, "active_vacancies": []})
    employers[user_id]["active_vacancies"].append(vacancy)
    await message.answer(f"✅ Вакансия размещена!\nКонтакт: @{contact}", reply_markup=main_menu)
    await state.clear()

@dp.message(F.text == "📋 Мои вакансии")
async def my_vacancies(message: types.Message):
    user_id = message.from_user.id
    emp = employers.get(user_id, {"active_vacancies": []})
    vac_list = emp.get("active_vacancies", [])
    if not vac_list:
        await message.answer("У вас нет активных вакансий.")
        return
    for idx, vac in enumerate(vac_list, start=1):
        text = f"💼 {vac['position']} ({vac['level']})\n📍 {vac['city']} | {vac['salary']}\n📊 Статус: {vac['status']}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👁️ Просмотреть кандидатов", callback_data=f"view_cand:{idx-1}"), InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_vac:{idx-1}")], [InlineKeyboardButton(text="💬 Написать в Telegram", url=f"https://t.me/{vac['contact']}")]])
        await message.answer(text, reply_markup=kb)

@dp.callback_query(lambda c: c.data and c.data.startswith("view_cand:"))
async def view_candidates(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    emp = employers.get(user_id, {"active_vacancies": []})
    vac_index = int(callback.data.split(":")[1])
    vac = emp["active_vacancies"][vac_index]
    if not vac["candidates"]:
        await callback.message.answer("Пока нет кандидатов на эту вакансию.")
        return
    cand_id = vac["candidates"][0]
    cand_data = seekers.get(cand_id)
    if not cand_data:
        await callback.message.answer("Данные кандидата недоступны.")
        return
    await callback.message.answer(f"👤 Кандидат:\nСпециальность: {cand_data['specialty']}\nУровень: {cand_data['level']}\nЖелаемая зарплата: {cand_data['salary']} ₸")

@dp.callback_query(lambda c: c.data and c.data.startswith("delete_vac:"))
async def delete_vacancy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    vac_index = int(callback.data.split(":")[1])
    emp = employers.get(user_id, {"active_vacancies": []})
    if vac_index < len(emp["active_vacancies"]):
        emp["active_vacancies"].pop(vac_index)
        await callback.message.answer("✅ Вакансия удалена.")

@dp.message(F.text == "⬅️ Назад")
async def go_back(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == SeekerStates.choosing_level.state:
        kb = nav_keyboard([[KeyboardButton(text=s)] for s in specialties])
        await message.answer("Выберите специальность:", reply_markup=kb)
        await state.set_state(SeekerStates.choosing_specialty)
    elif current_state == SeekerStates.choosing_salary.state:
        kb = nav_keyboard([[KeyboardButton(text=l)] for l in levels])
        await message.answer("Выберите уровень опыта:", reply_markup=kb)
        await state.set_state(SeekerStates.choosing_level)
    elif current_state == SeekerStates.uploading_cv.state:
        await message.answer("Укажите желаемую зарплату:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(SeekerStates.choosing_salary)
    elif current_state == EmployerStates.choosing_level.state:
        await message.answer("Напишите описание вакансии:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(EmployerStates.typing_description)
    elif current_state == EmployerStates.choosing_city.state:
        kb = nav_keyboard([[KeyboardButton(text=l)] for l in levels])
        await message.answer("Выберите уровень опыта:", reply_markup=kb)
        await state.set_state(EmployerStates.choosing_level)
    elif current_state == EmployerStates.choosing_format.state:
        kb = nav_keyboard([[KeyboardButton(text=c)] for c in cities])
        await message.answer("Выберите город:", reply_markup=kb)
        await state.set_state(EmployerStates.choosing_city)
    elif current_state == EmployerStates.typing_link.state:
        kb = nav_keyboard([[KeyboardButton(text=f)] for f in work_formats])
        await message.answer("Выберите формат работы:", reply_markup=kb)
        await state.set_state(EmployerStates.choosing_format)

@dp.message(F.text == "🏠 Главное меню")
async def go_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu)

async def main():
    if not os.path.exists("cv_files"):
        os.mkdir("cv_files")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
