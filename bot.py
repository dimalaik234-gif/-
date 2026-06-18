import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode

TOKEN = "8816734888:AAG6gApnQMqt01gfkzM-O1-L43cFnBytdgk"  # <--- ВСТАВЬ СВОЙ ТОКЕН СЮДА
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT, coins INTEGER, active_talisman TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (user_id INTEGER, talisman TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- КАТАЛОГ ТАЛИСМАНОВ ---
TALISMANS = {
    "common": ["Магия огня", "Магия воды", "Магия пердежа"],
    "rare": ["Магия ориентации", "Магия памяти", "Магия телекинез", "Урон 1.25x", "Здоровье 1.25x"],
    "epic": ["Магия жидкости", "Магия пламени", "Магия света", "Телекинез + Память"],
    "legendary": ["Талисман возрождения", "Щит на 5 сек"],
    "secret": ["Талисман Васи бога"]
}

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
def get_user(user_id):
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def register_user(user_id, username):
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    # Даем 50 монет на старте для покупки первого сундука
    c.execute("INSERT OR IGNORE INTO users (id, username, coins, active_talisman) VALUES (?, ?, ?, ?)",
              (user_id, username, 50, "Нет талисмана"))
    conn.commit()
    conn.close()

# --- КЛАВИАТУРЫ (КНОПКИ) ---
def main_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🛒 Магазин сундуков", callback_data="shop")],
        [InlineKeyboardButton(text="📖 Как играть? (Обучение)", callback_data="tutorial")]
    ])
    return kb

def shop_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Купить сундук (50 🪙)", callback_data="buy_chest")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])
    return kb

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])

# --- КОМАНДА СТАРТ И МЕНЮ ---
@dp.message(Command("start"))
async def start_cmd(message: Message):
    if message.chat.type != "private":
        return await message.answer("Напиши мне в личные сообщения, чтобы открыть меню: @"+(await bot.me()).username)
    
    register_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "👋 **Добро пожаловать в Битву Талискуба!**\n\n"
        "Здесь ты собираешь магические талисманы и сражаешься с друзьями в группах. "
        "Я выдал тебе стартовые **50 🪙**, чтобы ты мог купить свой первый талисман.\n\n"
        "Выбери действие ниже:",
        reply_markup=main_menu_kb(),
        parse_mode=ParseMode.MARKDOWN
    )

# --- ОБРАБОТКА КНОПОК ---
@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()

@dp.callback_query(F.data == "tutorial")
async def cb_tutorial(callback: CallbackQuery):
    text = (
        "📖 **Обучение**\n\n"
        "1️⃣ **Добыча:** В магазине ты покупаешь сундуки за монеты. Оттуда выпадают талисманы разной редкости.\n"
        "2️⃣ **Экипировка:** В профиле посмотри свои талисманы. Чтобы надеть его, напиши команду: `/equip Название`\n"
        "3️⃣ **Сражения:** Добавь меня в любую группу. Ответь на сообщение друга командой `/battle`, чтобы вызвать его на дуэль!\n"
        "4️⃣ **Секреты:** Победители боев имеют 5% шанс получить секретный *Талисман Васи бога*."
    )
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("SELECT talisman FROM inventory WHERE user_id=?", (callback.from_user.id,))
    inv = [row[0] for row in c.fetchall()]
    conn.close()

    inv_text = ", ".join(inv) if inv else "Пусто"
    
    text = (
        f"👤 **Профиль игрока** @{user[1]}\n\n"
        f"💰 Баланс: **{user[2]} 🪙**\n"
        f"⚔️ Активный талисман: **{user[3]}**\n\n"
        f"🎒 **Твой инвентарь:**\n{inv_text}\n\n"
        f"💡 *Чтобы надеть талисман, напиши боту:*\n`/equip Название`"
    )
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(F.data == "shop")
async def cb_shop(callback: CallbackQuery):
    text = (
        "🛒 **Магазин сундуков**\n\n"
        "Здесь ты можешь испытать удачу. Каждый сундук стоит 50 монет.\n"
        "Шансы:\n"
        "🟤 Обычные: 70%\n"
        "🔵 Редкие: 20%\n"
        "🟣 Эпические: 10%\n"
        "*(Легендарные пока не завезли в этот сундук)*"
    )
    await callback.message.edit_text(text, reply_markup=shop_kb(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(F.data == "buy_chest")
async def cb_buy_chest(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if user[2] < 50:
        await callback.answer("❌ Недостаточно монет!", show_alert=True)
        return

    # Генерация редкости
    rand_val = random.random()
    if rand_val < 0.7: rarity = "common"
    elif rand_val < 0.9: rarity = "rare"
    else: rarity = "epic"
    
    new_talisman = random.choice(TALISMANS[rarity])
    
    # Обновление БД
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins - 50 WHERE id=?", (callback.from_user.id,))
    c.execute("INSERT INTO inventory (user_id, talisman) VALUES (?, ?)", (callback.from_user.id, new_talisman))
    
    # Если это первый талисман, надеваем его автоматически
    if user[3] == "Нет талисмана":
        c.execute("UPDATE users SET active_talisman = ? WHERE id=?", (new_talisman, callback.from_user.id))
        extra_msg = f"\n\n✅ Талисман **{new_talisman}** автоматически экипирован!"
    else:
        extra_msg = ""
        
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"🎉 **Сундук открыт!**\nТебе выпал талисман: **{new_talisman}** 🔮{extra_msg}",
        reply_markup=back_kb(),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

# --- КОМАНДА ЭКИПИРОВКИ ---
@dp.message(Command("equip"))
async def equip_cmd(message: Message):
    talisman_name = message.text.replace("/equip", "").strip()
    if not talisman_name:
        return await message.answer("⚠️ Напиши название талисмана после команды. Пример:\n`/equip Магия огня`", parse_mode=ParseMode.MARKDOWN)
    
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("SELECT talisman FROM inventory WHERE user_id=? AND talisman=?", (message.from_user.id, talisman_name))
    has_talisman = c.fetchone()
    
    if not has_talisman:
        conn.close()
        return await message.answer(f"❌ В твоем инвентаре нет талисмана **{talisman_name}**.", parse_mode=ParseMode.MARKDOWN)
    
    c.execute("UPDATE users SET active_talisman = ? WHERE id=?", (talisman_name, message.from_user.id))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ Ты успешно надел талисман: **{talisman_name}**!", parse_mode=ParseMode.MARKDOWN)

# --- ПРИВЕТСТВИЕ В ГРУППЕ ---
@dp.message(F.new_chat_members)
async def group_greeting(message: Message):
    for new_member in message.new_chat_members:
        if new_member.id == bot.id:
            await message.answer(
                "Всем привет! 🔮 Я — бот **Битвы Талискуба**.\n\n"
                "Чтобы сразиться с кем-то в этом чате, ответьте на его сообщение командой `/battle`.\n"
                "Если у вас еще нет талисманов, напишите мне в личные сообщения команду `/start`!",
                parse_mode=ParseMode.MARKDOWN
            )

# --- БОЙ В ГРУППЕ ---
@dp.message(Command("battle"))
async def battle_cmd(message: Message):
    if message.chat.type == "private":
        return await message.answer("❌ Битвы возможны только в группах! Добавь меня в чат с друзьями.")
    if not message.reply_to_message:
        return await message.answer("❌ Чтобы атаковать, ответь командой `/battle` на сообщение соперника!", parse_mode=ParseMode.MARKDOWN)
    
    p1 = message.from_user
    p2 = message.reply_to_message.from_user
    
    if p1.id == p2.id:
        return await message.answer("Ты не можешь драться сам с собой!")

    user1 = get_user(p1.id)
    user2 = get_user(p2.id)
    
    if not user1 or user1[3] == "Нет талисмана":
        return await message.answer(f"⚠️ @{p1.username}, у тебя нет активного талисмана! Зайди в бота и купи его.")
    if not user2 or user2[3] == "Нет талисмана":
        return await message.answer(f"⚠️ @{p2.username} еще не готов к битве (нет активного талисмана)!")

    winner_id = random.choice([p1.id, p2.id])
    winner = p1 if winner_id == p1.id else p2
    loser = p2 if winner_id == p1.id else p1

    battle_log = (
        f"⚔️ **БИТВА ТАЛИСКУБОВ!** ⚔️\n\n"
        f"🧙‍♂️ @{p1.username} достает **{user1[3]}**\n"
        f"🧙‍♂️ @{p2.username} использует **{user2[3]}**\n\n"
        f"💥 В результате мощного столкновения побеждает @{winner.username}!"
    )

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
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
