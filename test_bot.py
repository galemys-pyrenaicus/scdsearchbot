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
    dinfo, dcribs = get_data(call.data)
    dinfo_msg = "\nAuthor: " + dinfo[0] + "\nType: " + dinfo[1] + "\nSet: " + dinfo[2] + "\nCouples: " + dinfo[3]
    bot.send_message(call.message.chat.id, dinfo_msg)
    for row in dcribs:
        crib_msg = "Source: " + row[0] + '\n\n' + row[1]
        bot.send_message(call.message.chat.id, crib_msg)
    png_url = "https://my.strathspey.org/dd/diagram/kr/" + str(call.data) + "/?f=png&w=800"
    try:
        bot.send_photo(call.message.chat.id, png_url)
    except:
        logging.warning('PNG not found')


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
  menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
  if header_buttons:
    menu.insert(0, header_buttons)
  if footer_buttons:
    menu.append(footer_buttons)
  return menu

def get_data(danceid):
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()
    sql_file = open(scddata)
    sql_as_string = sql_file.read()
    cursor.executescript(sql_as_string)
    cribs = []
    src_list = ""
    # DEFINE QUERIES
    # ---------------------------------------------------#
    dancelist_query = "SELECT id, text FROM dancecrib WHERE dance_id='%s'" % danceid
    cribsrc_query = """ select dancecribsource.name 
                            from dancecribsource
                            join dancecrib
                            on dancecrib.source_id = dancecribsource.id
                            where dancecrib.id IN (%s)"""
    author_query = "select person.name from dance join person on dance.devisor_id = person.id where dance.id = '%s'" % danceid
    type_query = "select dancetype.name from dance join dancetype on dance.type_id = dancetype.id where dance.id = '%s'" % danceid
    set_query = "select shape.name from dance join shape on dance.shape_id = shape.id where dance.id = '%s'" % danceid
    cpls_query = "select couples.name from dance join couples on dance.couples_id = couples.id where dance.id = '%s'" % danceid

    # ---------------------------------------------------#
    dancelist = cursor.execute(dancelist_query).fetchall()
    for row in dancelist:
        src_list = src_list + str(row[0]) + ',' #-------Getting list on cribs' id for cribsources query
    cribsources = cursor.execute(cribsrc_query % (src_list[:-1])).fetchall()
    dauthor = cursor.execute(author_query).fetchall()
    dtype = cursor.execute(type_query).fetchall()
    dset = cursor.execute(set_query).fetchall()
    dcpls = cursor.execute(cpls_query).fetchall()
    dance_info = (dauthor[0][0], dtype[0][0], dset[0][0], dcpls[0][0])
    i = 0
    for row in dancelist: #---------Concatenating crib texts and crib sources to one list
        cribs.append((cribsources[i][0], row[1]))
        i = i + 1
    return dance_info, cribs

bot.polling()