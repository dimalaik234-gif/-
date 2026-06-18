import asyncio
import random
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode

TOKEN = "8816734888:AAG6gApnQMqt01gfkzM-O1-L43cFnBytdgk"  # <--- ВСТАВЬ СВОЙ ТОКЕН
ADMIN_ID = 7184353531  # <--- ВСТАВЬ СВОЙ TELEGRAM ID (ЧИСЛАМИ)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    # Таблица пользователей (добавлено поле last_bonus для сохранения даты)
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT, coins INTEGER, active_talisman TEXT, last_bonus TEXT)''')
    # Таблица инвентаря
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
    # Регистрируем: даем 50 монет, пустой талисман и дефолтную дату бонуса
    c.execute("INSERT OR IGNORE INTO users (id, username, coins, active_talisman, last_bonus) VALUES (?, ?, ?, ?, ?)",
              (user_id, username, 50, "Нет талисмана", "1970-01-01"))
    conn.commit()
    conn.close()

# --- КНОПКИ ---
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily_bonus")],
        [InlineKeyboardButton(text="🛒 Магазин сундуков", callback_data="shop")],
        [InlineKeyboardButton(text="📖 Обучение", callback_data="tutorial")]
    ])

def shop_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Обычный сундук (50 🪙)", callback_data="buy_chest_common")],
        [InlineKeyboardButton(text="👑 Легендарный сундук (300 🪙)", callback_data="buy_chest_legendary")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
    ])

# --- КОМАНДЫ ЛС ---
@dp.message(Command("start"))
async def start_cmd(message: Message):
    if message.chat.type != "private":
        return await message.answer("Напиши мне в личку, чтобы открыть меню: @"+(await bot.me()).username)
    
    register_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "🔮 **Приветствуем в Битве Талискуба!**\n\n"
        "Управляй своими талисманами, забирай ежедневные бонусы и сражайся на аренах в группах.\n"
        "Тебе начислено стартовых **50 🪙**!",
        reply_markup=main_menu_kb(),
        parse_mode=ParseMode.MARKDOWN
    )

# --- ОБРАБОТКА МЕНЮ ---
@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text("🔮 Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()

@dp.callback_query(F.data == "tutorial")
async def cb_tutorial(callback: CallbackQuery):
    text = (
        "📖 **Краткое обучение:**\n\n"
        "1️⃣ Зайди в **Магазин** и купи сундук, чтобы получить свой первый талисман.\n"
        "2️⃣ Чтобы надеть его, напиши боту в личку команду: `/equip Название`\n"
        "3️⃣ Добавь бота в группу. Ответь на сообщение друга командой `/battle`.\n"
        "4️⃣ Победитель боя получает **+25 🪙** и 5% шанс выбить секретный *Талисман Васи бога*!"
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

    inv_text = ", ".join(inv) if inv else "Инвентарь пуст"
    text = (
        f"👤 **Профиль игрока:** @{user[1]}\n\n"
        f"💰 Баланс: **{user[2]} 🪙**\n"
        f"⚔️ Экипирован: **{user[3]}**\n\n"
        f"🎒 **Твоя коллекция:**\n_{inv_text}_\n\n"
        f"💡 *Сменить талисман:* `/equip Название`"
    )
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

# --- ЕЖЕДНЕВНЫЙ БОНУС ---
@dp.callback_query(F.data == "daily_bonus")
async def cb_daily_bonus(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    today = datetime.today().strftime('%Y-%m-%d')
    
    if user[4] == today:
        await callback.answer("❌ Ты уже забирал бонус сегодня! Приходи завтра.", show_alert=True)
        return
        
    bonus_coins = random.randint(20, 60)
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + ?, last_bonus = ? WHERE id = ?", (bonus_coins, today, callback.from_user.id))
    conn.commit()
    conn.close()
    
    await callback.answer(f"🎉 Успешно! Получено {bonus_coins} 🪙", show_alert=True)
    # Обновляем текст профиля/меню
    await callback.message.edit_text(f"🔮 Главное меню:\n\nВы успешно забрали бонус! (+{bonus_coins} 🪙)", reply_markup=main_menu_kb())

# --- МАГАЗИН СУНДУКОВ ---
@dp.callback_query(F.data == "shop")
async def cb_shop(callback: CallbackQuery):
    text = (
        "🛒 **Магазин Талискуба**\n\n"
        "📦 *Обычный сундук (50 🪙)* — Шанс на Обычный (70%), Редкий (20%), Эпический (10%).\n"
        "👑 *Легендарный сундук (300 🪙)* — 100% шанс получить один из Легендарных талисманов!"
    )
    await callback.message.edit_text(text, reply_markup=shop_kb(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_chest_"))
async def cb_buy_chest(callback: CallbackQuery):
    chest_type = callback.data.split("_")[2]
    user = get_user(callback.from_user.id)
    price = 50 if chest_type == "common" else 300
    
    if user[2] < price:
        await callback.answer("❌ Недостаточно монет!", show_alert=True)
        return

    if chest_type == "common":
        rand = random.random()
        rarity = "common" if rand < 0.7 else "rare" if rand < 0.9 else "epic"
        new_talisman = random.choice(TALISMANS[rarity])
    else:
        new_talisman = random.choice(TALISMANS["legendary"])
        
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (price, callback.from_user.id))
    c.execute("INSERT INTO inventory (user_id, talisman) VALUES (?, ?)", (callback.from_user.id, new_talisman))
    
    extra = ""
    if user[3] == "Нет талисмана":
        c.execute("UPDATE users SET active_talisman = ? WHERE id = ?", (new_talisman, callback.from_user.id))
        extra = f"\n\n✅ Талисман **{new_talisman}** автоматически надет!"
        
    conn.commit()
    conn.close()

    await callback.message.edit_text(f"🎁 Сундук открыт! Твой дроп: **{new_talisman}**{extra}", reply_markup=back_kb(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

# --- СМЕНА ТАЛИСМАНА ---
@dp.message(Command("equip"))
async def equip_cmd(message: Message):
    talisman_name = message.text.replace("/equip", "").strip()
    if not talisman_name:
        return await message.answer("⚠️ Пример команды:\n`/equip Магия огня`", parse_mode=ParseMode.MARKDOWN)
    
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("SELECT talisman FROM inventory WHERE user_id=? AND talisman=?", (message.from_user.id, talisman_name))
    if not c.fetchone():
        conn.close()
        return await message.answer(f"❌ У тебя нет талисмана **{talisman_name}**!")
    
    c.execute("UPDATE users SET active_talisman = ? WHERE id = ?", (talisman_name, message.from_user.id))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Успешно экипирован: **{talisman_name}**!")

# --- ГРУППОВЫЕ МЕХАНИКИ ---
@dp.message(F.new_chat_members)
async def greeting(message: Message):
    for member in message.new_chat_members:
        if member.id == bot.id:
            await message.answer("🔮 **Бот Битвы Талискуба успешно добавлен!**\n\nЧтобы устроить дуэль, ответьте на сообщение игрока командой `/battle`.\nКупить талисманы можно в ЛС бота: `/start`")

@dp.message(Command("battle"))
async def battle_cmd(message: Message):
    if message.chat.type == "private":
        return await message.answer("❌ Битвы проходят только в группах!")
    if not message.reply_to_message:
        return await message.answer("❌ Ответь командой `/battle` на сообщение соперника!")
        
    p1, p2 = message.from_user, message.reply_to_message.from_user
    if p1.id == p2.id: return await message.answer("Нельзя атаковать себя!")
    
    u1, u2 = get_user(p1.id), get_user(p2.id)
    if not u1 or u1[3] == "Нет талисмана": return await message.answer(f"⚠️ @{p1.username}, надень талисман в ЛС!")
    if not u2 or u2[3] == "Нет талисмана": return await message.answer(f"⚠️ У @{p2.username} нет активного талисмана!")

    winner = random.choice([p1, p2])
    loser = p2 if winner.id == p1.id else p1
    
    # Начисление +25 монет победителю в БД
    conn = sqlite3.connect("talisman_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + 25 WHERE id = ?", (winner.id,))
    
    log = (
        f"⚔️ **ДУЭЛЬ НА АРЕНЕ!** ⚔️\n\n"
        f"🧙‍♂️ @{p1.username} применил: **{u1[3]}**\n"
        f"🧙‍♂️ @{p2.username} применил: **{u2[3]}**\n\n"
        f"🎉 Победу одерживает @{winner.username}! Он забирает награду в **+25 🪙**"
    )

    # 5% Шанс на Секретный дроп Васи Бога
    if random.random() < 0.05:
        c.execute("INSERT INTO inventory (user_id, talisman) VALUES (?, ?)", (winner.id, "Талисман Васи бога"))
        log += f"\n\n🤯 **ШОК!** С небес спустился **Талисман Васи бога** и попал в инвентарь к @{winner.username}!"
        
    conn.commit()
    conn.close()
    await message.answer(log, parse_mode=ParseMode.MARKDOWN)

# --- АДМИН-КОМАНДА (Выдача монет) ---
@dp.message(Command("give_coins"))
async def admin_give_coins(message: Message):
    if message.from_user.id != ADMIN_ID:
        return # Игнорируем не-админов
    
    try:
        args = message.text.split()
        target_id = int(args[1])
        amount = int(args[2])
        
        conn = sqlite3.connect("talisman_bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, target_id))
        conn.commit()
        conn.close()
        
        await message.answer(f"✅ Успешно начислено **{amount} 🪙** пользователю с ID `{target_id}`", parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await message.answer("⚠️ Ошибка. Пример команды:\n`/give_coins 123456789 100`", parse_mode=ParseMode.MARKDOWN)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
