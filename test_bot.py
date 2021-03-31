from datetime import datetime

import telebot
import sqlite3
import requests
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging
import sys

logformat = ['%(asctime)s [%(levelname)s] - %(message)s', '%d-%b-%y %H:%M:%S']
logging.basicConfig(filename='/var/log/scdsearch.log', format=logformat[0], level='INFO', datefmt=logformat[1])

name = ''
scddata = '/opt/scdsearchbot/scddata-2.0.sql'
tokenpath = '/opt/scdsearchbot/token'
QIpath = '/opt/scdsearchbot/'

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
    QI_search = open(QIpath+'QI_search', 'a')
    QI_search.write(str(datetime.now()) + ' : ' + name + '\n')
    QI_search.close()
    try:
        for row in cursor.execute("SELECT name, id FROM dance WHERE ucname LIKE ?", ('%'+name.replace('\'', '').upper()+'%',)):
            button_list.append(InlineKeyboardButton(str(row[0]), callback_data=str(row[1])))
        reply_markup = InlineKeyboardMarkup(
        build_menu(button_list, n_cols=1))
        bot.send_message(message.from_user.id, 'Choose the dance:', reply_markup=reply_markup)
    except:
        bot.send_message(message.from_user.id, 'Too many dances, please specify the search query')


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    dinfo, dcribs = get_data(call.data)
    dinfo_msg = dinfo[5] + "\n\nAuthor:" + dinfo[0] + "\nType: " + dinfo[1] + "\nSet: " + dinfo[2] + "\nCouples: " + dinfo[3]
    if dinfo[4]:
        dinfo_msg = dinfo_msg + "\nMedley: " + dinfo[4]
    bot.send_message(call.message.chat.id, dinfo_msg)
    if not dcribs:
        bot.send_message(call.message.chat.id, 'No cribs available')
    else:
        for row in dcribs:
            crib_msg = "Source: " + row[0] + '\n\n' + row[1]
            bot.send_message(call.message.chat.id, crib_msg)
    png_url = get_image(str(call.data))
    if png_url: bot.send_photo(call.message.chat.id, png_url)
    QI_result = open(QIpath+'QI_result', 'a')
    QI_result.write(str(datetime.now()) + ' : ' + dinfo[5] + '\n')
    QI_result.close()


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
    medley = ''
    # DEFINE QUERIES
    # ---------------------------------------------------#
    dancelist_query = "SELECT id, text FROM dancecrib WHERE dance_id='%s'" % danceid
    cribsrc_query = """ select dancecribsource.name 
                            from dancecribsource
                            join dancecrib
                            on dancecrib.source_id = dancecribsource.id
                            where dancecrib.id IN (%s)"""
    dname_query = "select name from dance where dance.id = '%s'" % danceid
    author_query = "select person.name from dance join person on dance.devisor_id = person.id where dance.id = '%s'" % danceid
    type_query = "select dancetype.name, dancetype.id from dance join dancetype on dance.type_id = dancetype.id where dance.id = '%s'" % danceid
    set_query = "select shape.name from dance join shape on dance.shape_id = shape.id where dance.id = '%s'" % danceid
    cpls_query = "select couples.name from dance join couples on dance.couples_id = couples.id where dance.id = '%s'" % danceid
    medley_query = "select medleytype.description from dance join medleytype on dance.medleytype_id = medleytype.id where dance.id = '%s'" % danceid
    # ---------------------------------------------------#
    dancelist = cursor.execute(dancelist_query).fetchall()
    for row in dancelist:
        src_list = src_list + str(row[0]) + ','  # -------Getting list on cribs' id for cribsources query
    cribsources = cursor.execute(cribsrc_query % (src_list[:-1])).fetchall()
    dauthor = cursor.execute(author_query).fetchall()
    dtype = cursor.execute(type_query).fetchall()
    dset = cursor.execute(set_query).fetchall()
    dcpls = cursor.execute(cpls_query).fetchall()
    dname = cursor.execute(dname_query).fetchall()
    if (dtype[0][1] == 4):
        medley = cursor.execute(medley_query).fetchall()[0][0]
    dance_info = (dauthor[0][0], dtype[0][0], dset[0][0], dcpls[0][0], medley, dname[0][0])
    i = 0
    for row in dancelist:  # ---------Concatenating crib texts and crib sources to one list
        cribs.append((cribsources[i][0], row[1]))
        i = i + 1
    return dance_info, cribs


def get_image(id):
    png_url = "https://my.strathspey.org/dd/diagram/%s/" + str(id) + "/?f=png&w=800"
    for type in ['kr', 'scddb']:
        request = requests.get(png_url % type)
        if (request.status_code == 200):
            return png_url % type
    return False


bot.polling()
