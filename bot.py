import asyncio
import random
import sqlite3
import time
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ (ЗАПОЛНИ СВОИ ДАННЫЕ) ---
TOKEN = "8816734888:AAG6gApnQMqt01gfkzM-O1-L43cFnBytdgk" 
ADMIN_ID = 7184353531  # Твой Telegram ID (только цифры)

# Включаем логирование, чтобы видеть ошибки на сервере
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Словарь для анти-спама (кулдауны)
battle_cooldowns = {}

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("talisman_bot.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, coins INTEGER, active_talisman TEXT, last_bonus TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (user_id INTEGER, talisman TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- ТАЛИСМАНЫ И ИХ ОПИСАНИЯ ---
TALISMANS = {
    "common": {
        "Магия огня": "Уголек, обжигающий ладони.",
        "Магия воды": "Бурлящая вода для спокойствия.",
        "Магия пердежа": "Мощный звук, повергающий в шок."
    },
    "rare": {
        "Магия ориентации": "Компас к шаурмичной.",
        "Магия памяти": "Нить, хранящая ошибки врага.",
        "Магия телекинез": "Камень, левитирующий в руке.",
        "Урон 1.25x": "Заточенный обсидиановый нож.",
        "Здоровье 1.25x": "Кусочек брони дракона."
    },
    "epic": {
        "Магия жидкости": "Нестабильный сгусток формы.",
        "Магия пламени": "Вечные языки огня в лампадке.",
        "Магия света": "Ослепительный кристалл истины.",
        "Телекинез + Память": "Слияние разума и физики."
    },
    "legendary": {
        "Талисман возрождения": "Феникс, дающий второй шанс.",
        "Щит на 5 сек": "Энергетический барьер."
    },
    "secret": ["Талисман Васи бога"]
}

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ БД ---
def get_user(user_id):
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

# --- КНОПКИ ---
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Ежедневный Бонус", callback_data="daily_bonus")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="📖 Обучение", callback_data="tutorial")]
    ])

# --- КОМАНДЫ ЛС ---
@dp.message(Command("start"))
async def start_cmd(message: Message):
    if message.chat.type != "private": 
        return await message.answer(f"Напиши мне в личку: @{(await bot.me()).username}")
    
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?)", 
              (message.from_user.id, message.from_user.username, 50, "Нет талисмана", "1970-01-01"))
    conn.commit()
    conn.close()
    
    await message.answer("🔮 **Добро пожаловать в Битву Талискуба!**\nТвой путь начинается с 50 монет.", reply_markup=main_menu_kb(), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text("🔮 Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("SELECT talisman FROM inventory WHERE user_id=?", (callback.from_user.id,))
    inv = [row[0] for row in c.fetchall()]
    conn.close()
    
    text = (f"👤 **@{user[1]}**\n"
            f"💰 Баланс: {user[2]} 🪙\n"
            f"⚔️ Активен: {user[3]}\n\n"
            f"🎒 Инвентарь:\n{', '.join(inv) if inv else 'Пусто'}\n\n"
            f"💡 _Сменить: /equip Название_")
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "daily_bonus")
async def cb_bonus(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    today = datetime.today().strftime('%Y-%m-%d')
    if user[4] == today: 
        return await callback.answer("❌ Бонус уже получен! Приходи завтра.", show_alert=True)
    
    coins = random.randint(20, 60)
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + ?, last_bonus = ? WHERE id = ?", (coins, today, callback.from_user.id))
    conn.commit()
    conn.close()
    
    await callback.answer(f"🎉 Успех! Получено {coins} монет!", show_alert=True)
    await callback.message.edit_text(f"🔮 Главное меню:\n\n✅ Бонус {coins} 🪙 зачислен!", reply_markup=main_menu_kb())

@dp.callback_query(F.data == "tutorial")
async def cb_tutorial(callback: CallbackQuery):
    text = ("📖 **Обучение**\n\n"
            "1️⃣ В магазине покупай сундуки.\n"
            "2️⃣ Надевай талисманы через команду `/equip Название`.\n"
            "3️⃣ В группе ответь на сообщение друга командой `/battle`.\n"
            "4️⃣ Победитель получает **25 🪙** и 5% шанс выбить секретный талисман Васябог!")
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "shop")
async def cb_shop(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Обычный (50 🪙)", callback_data="buy_common")],
        [InlineKeyboardButton(text="👑 Легендарный (300 🪙)", callback_data="buy_legendary")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    await callback.message.edit_text("🛒 **Магазин сундуков**\nВыбери сундук для покупки:", reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy(callback: CallbackQuery):
    chest_type = callback.data.split("_")[1]
    price = 50 if chest_type == "common" else 300
    user = get_user(callback.from_user.id)
    
    if user[2] < price:
        return await callback.answer("❌ Не хватает монет!", show_alert=True)

    if chest_type == "common":
        rand = random.random()
        rarity = "common" if rand < 0.7 else "rare" if rand < 0.9 else "epic"
        new_talisman = random.choice(list(TALISMANS[rarity].keys()))
    else:
        new_talisman = random.choice(list(TALISMANS["legendary"].keys()))

    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (price, callback.from_user.id))
    c.execute("INSERT INTO inventory VALUES (?, ?)", (callback.from_user.id, new_talisman))
    
    extra = ""
    if user[3] == "Нет талисмана":
        c.execute("UPDATE users SET active_talisman = ? WHERE id = ?", (new_talisman, callback.from_user.id))
        extra = "\n✅ Талисман автоматически надет!"
        
    conn.commit()
    conn.close()

    await callback.message.edit_text(f"🎁 **Сундук открыт!**\nВыпал: **{new_talisman}**{extra}", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]), 
                                     parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("equip"))
async def equip_cmd(message: Message):
    t_name = message.text.replace("/equip", "").strip()
    if not t_name: return await message.answer("⚠️ Пример: `/equip Магия огня`", parse_mode=ParseMode.MARKDOWN)
    
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("SELECT talisman FROM inventory WHERE user_id=? AND talisman=?", (message.from_user.id, t_name))
    if not c.fetchone():
        conn.close()
        return await message.answer(f"❌ У тебя нет: **{t_name}**!", parse_mode=ParseMode.MARKDOWN)
    
    c.execute("UPDATE users SET active_talisman = ? WHERE id = ?", (t_name, message.from_user.id))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Экипировано: **{t_name}**!", parse_mode=ParseMode.MARKDOWN)

# --- ГРУППОВЫЕ МЕХАНИКИ ---
@dp.message(F.new_chat_members)
async def greeting(message: Message):
    for member in message.new_chat_members:
        if member.id == bot.id:
            await message.answer("🔮 Бот **Битва Талискуба** в чате!\nДля дуэли: ответьте на сообщение друга командой `/battle`.")

# --- БОЙ (С АНТИ-СПАМОМ И ЗАДЕРЖКОЙ) ---
@dp.message(Command("battle"))
async def battle_cmd(message: Message):
    if message.chat.type == "private":
        return await message.answer("❌ Битвы только в группах!")
    if not message.reply_to_message:
        return await message.answer("❌ Ответь командой `/battle` на сообщение соперника!")
        
    p1 = message.from_user
    p2 = message.reply_to_message.from_user
    
    if p1.id == p2.id: return await message.answer("Нельзя бить себя!")

    # АНТИ-СПАМ СИСТЕМА (5 секунд кулдаун)
    current_time = time.time()
    if p1.id in battle_cooldowns and current_time - battle_cooldowns[p1.id] < 5:
        return await message.answer(f"⏳ @{p1.username}, магия перезаряжается! Подожди пару секунд.")
    battle_cooldowns[p1.id] = current_time

    u1, u2 = get_user(p1.id), get_user(p2.id)
    if not u1 or u1[3] == "Нет талисмана": return await message.answer(f"⚠️ @{p1.username}, надень талисман в ЛС бота!")
    if not u2 or u2[3] == "Нет талисмана": return await message.answer(f"⚠️ У @{p2.username} нет талисмана!")

    # КИНЕМАТОГРАФИЧНЫЙ БОЙ
    msg = await message.answer(f"⚔️ **Дуэль: @{p1.username} VS @{p2.username}!**")
    await asyncio.sleep(1.5)
    await msg.edit_text(f"⚡️ @{p1.username} кастует: **{u1[3]}**\n🛡 @{p2.username} отвечает: **{u2[3]}**")
    await asyncio.sleep(2)
    
    winner = random.choice([p1, p2])
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + 25 WHERE id = ?", (winner.id,))
    
    res = f"🎉 Победил **@{winner.username}**! Награда +25 🪙."
    
    # СЕКРЕТНЫЙ ДРОП 5%
    if random.random() < 0.05:
        c.execute("INSERT INTO inventory VALUES (?, ?)", (winner.id, TALISMANS["secret"][0]))
        res += f"\n\n🤯 **ЛЕГЕНДАРНАЯ УДАЧА!** С небес падает **{TALISMANS['secret'][0]}**!"
    
    conn.commit()
    conn.close()
    await msg.edit_text(res, parse_mode=ParseMode.MARKDOWN)

# --- АДМИН-КОМАНДА (ЗАЩИЩЕНА ОТ ОШИБОК) ---
@dp.message(Command("give_coins"))
async def give_coins(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        target_id = int(args[1])
        amount = int(args[2])
        
        conn = sqlite3.connect("talisman_bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, target_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Выдано {amount} 🪙 пользователю {target_id}")
    except (IndexError, ValueError):
        await message.answer("⚠️ Ошибка! Пиши так:\n`/give_coins ID_пользователя 100`", parse_mode=ParseMode.MARKDOWN)

async def main():
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
