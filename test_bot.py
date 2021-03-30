import telebot
import sqlite3
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging
import sys

logformat = ['%(asctime)s [%(levelname)s] - %(message)s', '%d-%b-%y %H:%M:%S']
logging.basicConfig(filename='/var/log/scdsearch.log', format=logformat[0], level='INFO', datefmt=logformat[1])

name = ''
scddata = '/opt/scdsearchbot/scddata-2.0.sql'
tokenpath = '/opt/scdsearchbot/token'

try:
    f = open(tokenpath, 'r')
    token = f.readline()
    bot = telebot.TeleBot(token.rstrip())
except:
    logging.error("Can't read the token")
    sys.exit()

try:
    f2 = open(scddata, 'r')
except:
    logging.error("Can't open SCDDATA")
    sys.exit()

logging.info("Service started")

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.register_next_step_handler(message, get_name)

@bot.message_handler(content_types=['text'])
def get_name(message): # получаем название танца
    global name
    name = message.text
    bot.send_message(message.from_user.id, "Looking for " + name + "...")
    get_list(message)


def get_list(message):
    global name
    button_list = []
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()
    sql_file = open(scddata)
    sql_as_string = sql_file.read()
    cursor.executescript(sql_as_string)
    like = " LIKE '%" + name.upper() + "%'"
    for row in cursor.execute("SELECT name, id FROM dance WHERE ucname" + like):
        button_list.append(InlineKeyboardButton(str(row[0]), callback_data=str(row[1])))
    reply_markup = InlineKeyboardMarkup(
    build_menu(button_list, n_cols=1))
    bot.send_message(message.from_user.id, 'Choose the dance:', reply_markup=reply_markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()
    sql_file = open(scddata)
    sql_as_string = sql_file.read()
    cursor.executescript(sql_as_string)
    where = " WHERE dance_id=" + call.data
    dancelist = cursor.execute("SELECT id, text FROM dancecrib" + where)
    query = """ SELECT dancecribsource.name 
                FROM dancecribsource
                JOIN dancecrib
                ON dancecrib.source_id = dancecribsource.id
                WHERE dancecrib.id = '"""
    for row in dancelist:
        cursor.execute(query + str(row[0]) + '\'')
        cribsrc = cursor.fetchone()
        print(row)
        bot.send_message(call.message.chat.id, "Source: " + cribsrc[0] + '\n\n' + row[1])

def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
  menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
  if header_buttons:
    menu.insert(0, header_buttons)
  if footer_buttons:
    menu.append(footer_buttons)
  return menu


bot.polling()