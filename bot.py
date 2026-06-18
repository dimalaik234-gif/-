import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode

TOKEN = "8816734888:AAG6gApnQMqt01gfkzM-O1-L43cFnBytdgk"  # Вставь сюда токен своего бота!
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT, coins INTEGER, active_talisman TEXT)''')
    # Таблица инвентаря
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (user_id INTEGER, talisman TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- КАТАЛОГ ТАЛИСМАНОВ ---
TALISMANS = {
    "common": ["Магия огня", "Магия воды", "Магия пердежа"],
    "rare": ["Магия ориентации", "Магия памяти", "Магия телекинез", "Талисман: урон 1.25x", "Талисман: здоровье 1.25x"],
    "epic": ["Магия жидкости", "Магия пламени", "Магия света", "Магия 2в1 (Телекинез + Память)"],
    "legendary": ["Талисман: возрождает", "Талисман: защита на 5 сек."],
    "secret": ["Талисман Васи бога"]
}

def get_user(user_id):
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(user_id, username):
    start_talisman = random.choice(TALISMANS["common"])
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (id, username, coins, active_talisman) VALUES (?, ?, ?, ?)",
              (user_id, username, 100, start_talisman))
    c.execute("INSERT OR IGNORE INTO inventory (user_id, talisman) VALUES (?, ?)", (user_id, start_talisman))
    conn.commit()
    conn.close()

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def start_cmd(message: Message):
    add_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "🔮 **Битва Талискуба началась!**\n\n"
        "Ты получил стартовый обычный талисман и 100 монет.\n"
        "📜 **Команды:**\n"
        "`/profile` - Твой профиль и инвентарь\n"
        "`/shop` - Купить сундук с талисманами\n"
        "`/battle` - Вызвать на дуэль (напиши в ответ на сообщение в группе!)",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала напиши /start")
    
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("SELECT talisman FROM inventory WHERE user_id=?", (message.from_user.id,))
    inv = [row[0] for row in c.fetchall()]
    conn.close()

    text = (
        f"👁‍🗨 **Твой профиль**\n\n"
        f"👤 Игрок: @{user[1]}\n"
        f"💰 Монеты: {user[2]} 🪙\n"
        f"✨ Активный талисман: **{user[3]}**\n\n"
        f"🎒 **Твои талисманы ({len(inv)} шт):**\n" + ", ".join(inv)
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("shop"))
async def shop_cmd(message: Message):
    # Упрощенная покупка для примера. Берет 50 монет и дает случайный талисман (Обычный/Редкий/Эпик)
    user = get_user(message.from_user.id)
    if not user: return
    
    if user[2] < 50:
        return await message.answer("❌ Недостаточно монет! Сундук стоит 50 🪙.")
    
    # Шансы: 70% Обычный, 20% Редкий, 10% Эпический (Леги только за дорогие сундуки, тут для примера)
    rand_val = random.random()
    if rand_val < 0.7: rarity = "common"
    elif rand_val < 0.9: rarity = "rare"
    else: rarity = "epic"
    
    new_talisman = random.choice(TALISMANS[rarity])
    
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins - 50 WHERE id=?", (message.from_user.id,))
    c.execute("INSERT INTO inventory (user_id, talisman) VALUES (?, ?)", (message.from_user.id, new_talisman))
    conn.commit()
    conn.close()

    await message.answer(f"🎁 Ты открыл сундук за 50 монет!\nВыпал талисман: **{new_talisman}**", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("battle"))
async def battle_cmd(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.answer("❌ Битвы возможны только в группах!")
    if not message.reply_to_message:
        return await message.answer("❌ Чтобы атаковать, ответь командой /battle на сообщение соперника!")
    
    p1 = message.from_user
    p2 = message.reply_to_message.from_user
    
    user1 = get_user(p1.id)
    user2 = get_user(p2.id)
    
    if not user1 or not user2:
        return await message.answer("⚠️ Оба игрока должны быть зарегистрированы в боте (написать /start в личку боту)!")

    # Симуляция боя
    winner_id = random.choice([p1.id, p2.id])
    winner = p1 if winner_id == p1.id else p2
    loser = p2 if winner_id == p1.id else p1

    battle_log = (
        f"⚔️ **БИТВА ТАЛИСКУБОВ!** ⚔️\n\n"
        f"🧙‍♂️ @{p1.username} достает **{user1[3]}**\n"
        f"🧙‍♂️ @{p2.username} использует **{user2[3]}**\n\n"
        f"💥 В результате мощного столкновения побеждает @{winner.username}!"
    )

    # СЕКРЕТНЫЙ ДРОП: 5% шанс получить Талисман Васи бога победителю
    if random.random() < 0.05:
        secret = TALISMANS["secret"][0]
        conn = sqlite3.connect("talisman_bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO inventory (user_id, talisman) VALUES (?, ?)", (winner.id, secret))
        conn.commit()
        conn.close()
        battle_log += f"\n\n🤯 **СЕКРЕТНАЯ НАГРАДА!** Боги заметили доблесть @{winner.username}, и ему выпадает: **{secret}**!"

    await message.answer(battle_log, parse_mode=ParseMode.MARKDOWN)

async def main():
    print("Бот Битвы Талискуба запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
