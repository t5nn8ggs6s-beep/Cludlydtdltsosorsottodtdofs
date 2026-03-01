import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8566271526:AAEcLjkNCAYB3gLLviEMAXN03tk1mHsamqU"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

deals = {}  # сделки в памяти
ratings = {}  # рейтинг продавцов: {username: [оценки]}

# Старт
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Создать сделку")],
            [types.KeyboardButton(text="Посмотреть рейтинг")],
            [types.KeyboardButton(text="Список сделок")]
        ],
        resize_keyboard=True
    )
    await message.answer("Добро пожаловать в бот сделок.", reply_markup=kb)

# Создать сделку
@dp.message(lambda m: m.text == "Создать сделку")
async def create_deal(message: types.Message):
    await message.answer("Введите @username продавца:")
    dp.message.register(process_seller)

async def process_seller(message: types.Message):
    seller = message.text.strip()
    await message.answer("Введите цену:")
    dp.message.register(lambda m: process_price(m, seller))

async def process_price(message: types.Message, seller):
    price = message.text.strip()
    await message.answer("Введите описание сделки:")
    dp.message.register(lambda m: process_description(m, seller, price))

async def process_description(message: types.Message, seller, price):
    description = message.text.strip()
    deal_id = len(deals) + 1

    deals[deal_id] = {
        "buyer": message.from_user.id,
        "seller_username": seller,
        "price": price,
        "description": description,
        "status": "pending"
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Принять", callback_data=f"accept_{deal_id}")],
        [InlineKeyboardButton(text="Отклонить", callback_data=f"decline_{deal_id}")]
    ])

    try:
        await bot.send_message(
            seller,
            f"Вам предлагают сделку\nЦена: {price}\nОписание: {description}",
            reply_markup=kb
        )
        await message.answer("Запрос отправлен продавцу.")
    except:
        await message.answer("Ошибка: продавец должен сначала написать боту /start.")

# Принять сделку
@dp.callback_query(lambda c: c.data.startswith("accept_"))
async def accept_deal(callback: types.CallbackQuery):
    deal_id = int(callback.data.split("_")[1])
    deal = deals.get(deal_id)

    if deal:
        deal["status"] = "accepted"
        buyer_id = deal["buyer"]

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить выполнение", callback_data=f"done_{deal_id}")]
        ])

        await bot.send_message(
            buyer_id,
            f"Продавец {deal['seller_username']} принял сделку.\nСвяжитесь в личке и после завершения подтвердите.",
            reply_markup=kb
        )

    await callback.answer("Вы приняли сделку.")

# Завершение сделки и рейтинг
@dp.callback_query(lambda c: c.data.startswith("done_"))
async def finish_deal(callback: types.CallbackQuery):
    deal_id = int(callback.data.split("_")[1])
    deal = deals.get(deal_id)

    if deal:
        deal["status"] = "completed"
        seller = deal['seller_username']
        buyer_id = deal['buyer']

        # Кнопки для оценки 1-5
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=str(i), callback_data=f"rate_{deal_id}_{i}") for i in range(1,6)]
        ])
        await bot.send_message(
            buyer_id,
            f"Сделка с {seller} завершена! Оцените продавца (1–5):",
            reply_markup=kb
        )
    await callback.answer()

# Получение оценки
@dp.callback_query(lambda c: c.data.startswith("rate_"))
async def rate_seller(callback: types.CallbackQuery):
    _, deal_id, score = callback.data.split("_")
    deal_id = int(deal_id)
    score = int(score)
    deal = deals.get(deal_id)

    if deal:
        seller = deal['seller_username']
        if seller not in ratings:
            ratings[seller] = []
        ratings[seller].append(score)
        await callback.message.edit_text(f"Вы оценили продавца {seller} на {score}⭐")

    await callback.answer()

# Просмотр рейтинга
@dp.message(lambda m: m.text == "Посмотреть рейтинг")
async def show_ratings(message: types.Message):
    if not ratings:
        await message.answer("Рейтинг пока пустой.")
        return
    text = "Рейтинг продавцов:\n"
    for seller, scores in ratings.items():
        avg = sum(scores)/len(scores)
        text += f"{seller}: {avg:.2f}⭐ ({len(scores)} оценок)\n"
    await message.answer(text)

# Список сделок
@dp.message(lambda m: m.text == "Список сделок")
async def show_deals(message: types.Message):
    user_id = message.from_user.id
    user_username = message.from_user.username
    text = "Ваши сделки:\n"
    has_deals = False
    for deal_id, deal in deals.items():
        if deal['buyer'] == user_id or deal['seller_username'] == f"@{user_username}":
            has_deals = True
            role = "Покупатель" if deal['buyer'] == user_id else "Продавец"
            text += f"ID: {deal_id} | {role} | Цена: {deal['price']} | Статус: {deal['status']}\n"
    if not has_deals:
        text += "Сделок нет."
    await message.answer(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
