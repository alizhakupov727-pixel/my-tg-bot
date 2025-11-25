from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import os
from datetime import datetime, timedelta

API_TOKEN = "8340476999:AAHvwY4YBn6YHkHwRHq0HCYHG82Gq5yPECo"
ADMIN_ID = 1475331727

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

seekers = {}
employers = {}
pending_vacancies = []

templates = {}  # {template_name: {"text":..., "audience":..., "filters":..., "count":...}}
scheduled_mailings = []  # [{"template":..., "time":..., "status":...}]

specialties = ["Backend Developer", "Frontend Developer", "DevOps Engineer", "QA Engineer", "Analytics", "Product Manager", "Designer"]
levels = ["Junior", "Middle", "Senior"]
cities = ["Алматы", "Астана", "Шымкент", "Караганда", "Актобе"]
work_formats = ["Офис", "Удаленка", "Гибрид"]

# -------------------- FSM --------------------
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

class AdminStates(StatesGroup):
    creating_template_name = State()
    creating_template_text = State()
    selecting_audience = State()
    preview_template = State()
    scheduling = State()
    confirm_audience = State()
    input_schedule_date = State()

# -------------------- Главное меню --------------------
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
        [KeyboardButton(text="⚙️ Админ-панель")],
        [KeyboardButton(text="🛠 Модерация")],
        [KeyboardButton(text="📊 Аналитика")]
    ], resize_keyboard=True
)

# -------------------- Функции --------------------
def nav_keyboard(buttons_list):
    kb = buttons_list + [[KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="🏠 Главное меню")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def audience_keyboard(selected=None):
    if selected is None:
        selected = set()
    buttons = [
        [InlineKeyboardButton(text=("✅ " if "seekers" in selected else "") + "👤 Все соискатели", callback_data="aud_seekers")],
        [InlineKeyboardButton(text=("✅ " if "employers" in selected else "") + "💼 Все работодатели", callback_data="aud_employers")]
    ]
    for s in specialties:
        buttons.append([InlineKeyboardButton(
            text=("✅ " if s in selected else "") + f"🎯 {s}",
            callback_data=f"aud_{s.replace(' ', '_')}"
        )])
    for l in levels:
        buttons.append([InlineKeyboardButton(
            text=("✅ " if l in selected else "") + f"🔹 {l}",
            callback_data=f"aud_level_{l}"
        )])
    buttons.append([
        InlineKeyboardButton(text="✅ Подтвердить аудиторию", callback_data="confirm_audience"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_text")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# -------------------- Старт --------------------
@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user and message.from_user.id == ADMIN_ID:
        await message.answer("Добро пожаловать, админ!", reply_markup=admin_menu)
    else:
        await message.answer("Добро пожаловать!", reply_markup=main_menu)

# -------------------- Админ-панель --------------------
@dp.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен.")
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📨 Массовые рассылки")],
            [KeyboardButton(text="📊 Статистика бота")],
            [KeyboardButton(text="🔙 Назад")]
        ], resize_keyboard=True
    )
    await message.answer("⚙️ Админ-панель:", reply_markup=kb)

# -------------------- Массовые рассылки --------------------
@dp.message(F.text == "📨 Массовые рассылки")
async def mailing_menu(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать шаблон")],
            [KeyboardButton(text="📋 Мои шаблоны")],
            [KeyboardButton(text="📅 Запланированные рассылки")],
            [KeyboardButton(text="🔙 Назад")]
        ], resize_keyboard=True
    )
    await message.answer("Меню рассылок:", reply_markup=kb)

# -------------------- Создание шаблона --------------------
@dp.message(F.text == "➕ Создать шаблон")
async def create_template_name(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.creating_template_name)
    await message.answer("Введите название шаблона:", reply_markup=ReplyKeyboardRemove())

@dp.message(AdminStates.creating_template_name)
async def save_template_name(message: types.Message, state: FSMContext):
    await state.update_data(template_name=message.text)
    await state.set_state(AdminStates.creating_template_text)
    await message.answer(
        "Введите текст шаблона. Вы можете использовать переменные: {name}, {specialty}, {count}"
    )

@dp.message(AdminStates.creating_template_text)
async def save_template_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    template_name = data.get("template_name")
    templates[template_name] = {"text": message.text, "audience": [], "filters": [], "count": 0}
    await state.clear()
    await message.answer(f"✅ Шаблон '{template_name}' создан!", reply_markup=admin_menu)

# -------------------- Мои шаблоны --------------------
@dp.message(F.text == "📋 Мои шаблоны")
async def my_templates(message: types.Message):
    if not templates:
        await message.answer("У вас нет шаблонов.")
        return
    for idx, (name, t) in enumerate(templates.items(), start=1):
        aud_list = t.get("audience", [])
        count = t.get("count", "Все")
        text = f"{idx}️⃣ {name}\n👥 {count} получателей | {', '.join(aud_list)}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👁 Просмотреть", callback_data=f"view:{name}")],
            [InlineKeyboardButton(text="📤 Отправить", callback_data=f"send_now:{name}")],
            [InlineKeyboardButton(text="📅 Запланировать", callback_data=f"schedule:{name}")],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{name}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{name}")]
        ])
        await message.answer(text, reply_markup=kb)

# -------------------- Запланировать рассылку --------------------
@dp.callback_query(lambda c: c.data.startswith("schedule:"))
async def schedule_template(callback: types.CallbackQuery, state: FSMContext):
    template_name = callback.data.split(":")[1]
    await state.update_data(schedule_template=template_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Отправить сейчас", callback_data="send_now")],
        [InlineKeyboardButton(text="📅 Запланировать на дату", callback_data="schedule_date")]
    ])
    await callback.message.answer("Когда отправить рассылку?", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "schedule_date")
async def input_schedule_date(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ\nНапример: 25.11.2024 14:30")
    await state.set_state(AdminStates.input_schedule_date)

@dp.message(AdminStates.input_schedule_date)
async def save_schedule_date(message: types.Message, state: FSMContext):
    try:
        dt = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        if dt < datetime.now():
            await message.answer("❌ Дата не может быть в прошлом. Попробуйте снова.")
            return
        data = await state.get_data()
        template_name = data.get("schedule_template")
        scheduled_mailings.append({
            "template": template_name,
            "time": dt,
            "status": "Ожидает отправки"
        })
        t = templates[template_name]
        count = t.get("count", "Все")
        await message.answer(f"✅ Рассылка запланирована!\n"
                             f"Шаблон: \"{template_name}\"\n"
                             f"Получатели: {count}\n"
                             f"Дата отправки: {dt.strftime('%d %B %Y, %H:%M')}\n"
                             f"Рассылка будет отправлена автоматически.",
                             reply_markup=ReplyKeyboardMarkup(
                                 keyboard=[[KeyboardButton(text="📋 К списку рассылок")],
                                           [KeyboardButton(text="➕ Создать ещё одну")]],
                                 resize_keyboard=True))
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат даты. Попробуйте ещё раз.")

# -------------------- Отправка рассылки --------------------
async def send_template(template_name):
    t = templates[template_name]
    audience = t.get("audience", [])
    count = t.get("count", 0)
    sent = 0
    for i in range(count):
        await asyncio.sleep(0.033)  # ~30 сообщений/сек
        # Здесь подставляем реальные данные пользователей
        # Пример:
        # user_id = get_user_id(audience[i])
        # text = t["text"].format(name=user_name, specialty=user_specialty, count=user_count)
        # await bot.send_message(user_id, text)
        sent += 1
    return sent

@dp.callback_query(lambda c: c.data.startswith("send_now:"))
async def send_now_callback(callback: types.CallbackQuery):
    template_name = callback.data.split(":")[1]
    await callback.message.answer(f"⚠️ Вы уверены, что хотите отправить рассылку?\nШаблон: \"{template_name}\"",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                      [InlineKeyboardButton(text="✅ Да, отправить", callback_data=f"confirm_send:{template_name}")],
                                      [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_send")]
                                  ]))

@dp.callback_query(lambda c: c.data.startswith("confirm_send:"))
async def confirm_send(callback: types.CallbackQuery):
    template_name = callback.data.split(":")[1]
    await callback.message.answer("📤 Отправка рассылки...")
    sent = await send_template(template_name)
    await callback.message.answer(f"✅ Рассылка завершена!\n📤 Отправлено: {sent}")

@dp.callback_query(lambda c: c.data == "cancel_send")
async def cancel_send(callback: types.CallbackQuery):
    await callback.message.answer("❌ Отправка отменена.")

# -------------------- Планировщик --------------------
async def scheduler():
    while True:
        now = datetime.now()
        for m in scheduled_mailings:
            if m["status"] == "Ожидает отправки" and m["time"] <= now:
                await send_template(m["template"])
                m["status"] = "Отправлено"
        await asyncio.sleep(60)  # Проверять каждую минуту
@dp.message(F.text == "Мой профиль")
async def my_profile(message: types.Message):
    if not message.from_user:
        return
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

    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")],
                                       [KeyboardButton(text="🏠 Главное меню")]
                                       ],
                             resize_keyboard=True)

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
    await message.answer("Укажите желаемую зарплату в ₸:",
                         reply_markup=ReplyKeyboardRemove())
    await state.set_state(SeekerStates.choosing_salary)


@dp.message(SeekerStates.choosing_salary)
async def choose_salary(message: types.Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Введите число, например: 450000")
        return
    await state.update_data(salary=int(message.text))
    await message.answer("Отправьте ваше CV (PDF, JPG, PNG):")
    await state.set_state(SeekerStates.uploading_cv)


@dp.message(F.content_type.in_(["document", "photo"]))
async def upload_cv(message: types.Message, state: FSMContext):
    if not message.from_user:
        return
    user_id = message.from_user.id
    if not os.path.exists("cv_files"):
        os.mkdir("cv_files")

    if message.document:
        if not message.document.file_name:
            await message.answer("Ошибка загрузки файла. Попробуйте снова.")
            return
        file_parts = message.document.file_name.split('.')
        if len(file_parts) < 2:
            await message.answer("Не удалось определить тип файла.")
            return
        ext = file_parts[-1]
        if ext.lower() not in ["pdf", "jpg", "png"]:
            await message.answer(
                "Я могу принять только PDF, JPG или PNG. Попробуйте снова.")
            return
        file_path = f"cv_files/{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        file = await bot.get_file(message.document.file_id)
        if file.file_path:
            await bot.download_file(file.file_path, destination=file_path)

    elif message.photo:
        file_path = f"cv_files/{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        file = await bot.get_file(message.photo[-1].file_id)
        if file.file_path:
            await bot.download_file(file.file_path, destination=file_path)

    await message.answer("✅ CV загружено!", reply_markup=main_menu)
    await state.clear()


@dp.message(F.text == "Ищу сотрудника")
async def employer_start(message: types.Message, state: FSMContext):
    kb = nav_keyboard([[KeyboardButton(text="➕ Разместить вакансию")],
                       [KeyboardButton(text="📋 Мои вакансии")]])
    await message.answer("Что вы хотите сделать?", reply_markup=kb)


@dp.message(F.text == "➕ Разместить вакансию")
async def post_vacancy_start(message: types.Message, state: FSMContext):
    kb = nav_keyboard([[KeyboardButton(text=s)] for s in specialties])
    await message.answer("Выберите должность:", reply_markup=kb)
    await state.set_state(EmployerStates.choosing_position)


@dp.message(EmployerStates.choosing_position, F.text.in_(specialties))
async def choose_position(message: types.Message, state: FSMContext):
    await state.update_data(position=message.text)
    await message.answer("Напишите описание вакансии:",
                         reply_markup=ReplyKeyboardRemove())
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
    await message.answer("Укажите зарплату:",
                         reply_markup=ReplyKeyboardRemove())
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
    await message.answer("Добавьте ссылку на вакансию или 'Нет':",
                         reply_markup=ReplyKeyboardRemove())
    await state.set_state(EmployerStates.typing_link)


@dp.message(EmployerStates.typing_link)
async def type_link(message: types.Message, state: FSMContext):
    if not message.from_user or not message.text:
        return
    await state.update_data(
        link=message.text if message.text.lower() != "нет" else "")
    user_id = message.from_user.id
    contact = message.from_user.username
    data = await state.get_data()
    vacancy = {
        "position": data["position"],
        "description": data["description"],
        "level": data["level"],
        "salary": data["salary"],
        "city": data["city"],
        "work_format": data["work_format"],
        "link": data["link"],
        "contact": contact,
        "candidates": [],
        "status": "✅ Активна"
    }
    employers.setdefault(user_id, {
        "username": message.from_user.username,
        "active_vacancies": []
    })
    employers[user_id]["active_vacancies"].append(vacancy)
    await message.answer(f"✅ Вакансия размещена!\nКонтакт: @{contact}",
                         reply_markup=main_menu)
    await state.clear()


@dp.message(F.text == "📋 Мои вакансии")
async def my_vacancies(message: types.Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    emp = employers.get(user_id, {"active_vacancies": []})
    vac_list = emp.get("active_vacancies", [])
    if not vac_list:
        await message.answer("У вас нет активных вакансий.")
        return
    for idx, vac in enumerate(vac_list, start=1):
        text = f"💼 {vac['position']} ({vac['level']})\n📍 {vac['city']} | {vac['salary']}\n📊 Статус: {vac['status']}"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="👁️ Просмотреть кандидатов",
                                     callback_data=f"view_cand:{idx-1}"),
                InlineKeyboardButton(text="🗑️ Удалить",
                                     callback_data=f"delete_vac:{idx-1}")
            ],
                             [
                                 InlineKeyboardButton(
                                     text="💬 Написать в Telegram",
                                     url=f"https://t.me/{vac['contact']}")
                             ]])
        await message.answer(text, reply_markup=kb)


@dp.callback_query(lambda c: c.data and c.data.startswith("view_cand:"))
async def view_candidates(callback: types.CallbackQuery):
    if not callback.from_user or not callback.data:
        return
    user_id = callback.from_user.id
    emp = employers.get(user_id, {"active_vacancies": []})
    vac_parts = callback.data.split(":")
    if len(vac_parts) < 2:
        return
    vac_index = int(vac_parts[1])
    vac = emp["active_vacancies"][vac_index]
    if not vac["candidates"]:
        if callback.message:
            await callback.message.answer(
                "Пока нет кандидатов на эту вакансию.")
        return
    cand_id = vac["candidates"][0]
    cand_data = seekers.get(cand_id)
    if not cand_data:
        if callback.message:
            await callback.message.answer("Данные кандидата недоступны.")
        return
    if callback.message:
        await callback.message.answer(
            f"👤 Кандидат:\nСпециальность: {cand_data['specialty']}\nУровень: {cand_data['level']}\nЖелаемая зарплата: {cand_data['salary']} ₸"
        )


@dp.callback_query(lambda c: c.data and c.data.startswith("delete_vac:"))
async def delete_vacancy(callback: types.CallbackQuery):
    if not callback.from_user or not callback.data:
        return
    user_id = callback.from_user.id
    vac_parts = callback.data.split(":")
    if len(vac_parts) < 2:
        return
    vac_index = int(vac_parts[1])
    emp = employers.get(user_id, {"active_vacancies": []})
    if vac_index < len(emp["active_vacancies"]):
        emp["active_vacancies"].pop(vac_index)
        if callback.message:
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
        await message.answer("Укажите желаемую зарплату:",
                             reply_markup=ReplyKeyboardRemove())
        await state.set_state(SeekerStates.choosing_salary)
    elif current_state == EmployerStates.choosing_level.state:
        await message.answer("Напишите описание вакансии:",
                             reply_markup=ReplyKeyboardRemove())
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

# -------------------- Запуск бота --------------------
async def main():
    if not os.path.exists("cv_files"):
        os.mkdir("cv_files")
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(scheduler())  # Запуск планировщика
    await dp.start_polling(bot, skip_updates=False)

if __name__ == "__main__":
    asyncio.run(main())
