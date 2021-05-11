from datetime import datetime
import re

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


@bot.message_handler(commands=['help'])
def start_message(message):
    bot.send_message(message.from_user.id, 'This bot is looking for SCD cribs')


# Get dance name from the user input
@bot.message_handler(content_types=['text'])
def get_name(message):
    global name
    name = message.text
    bot.send_message(message.from_user.id, "Looking for " + name + "...")
    get_list(message)


def get_list(message):
    global name
    button_list = []
    # connect to local database
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()
    cursor.execute("PRAGMA read_committed = true;")
    sql_file = open(scddata)
    sql_as_string = sql_file.read()
    cursor.executescript(sql_as_string)
    qi_search = open(QIpath+'QI_search', 'a')
    qi_search.write(str(datetime.now()) + ' : ' + name + '\n')
    qi_search.close()
    try:
        # Dances' names in the 'ucname' column are uppercase with apostrophe remove
        for row in cursor.execute("SELECT name, id FROM dance WHERE ucname LIKE ?", ('%'+name.replace('\'', '').upper()+'%',)):
            button_list.append(InlineKeyboardButton(str(row[0]), callback_data=str(row[1])))
        reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
        if not button_list:
            bot.send_message(message.from_user.id, 'No dance found. Please, try again')
        else:
            if len(button_list) == 1:  # If only one dance was found - send its crib to the user
                send_res_msg(button_list[0].callback_data, message.from_user.id)
            else:
                bot.send_message(message.from_user.id, 'Choose the dance:', reply_markup=reply_markup)
    except Exception as e:
        logging.error(str(e))
        bot.send_message(message.from_user.id, 'Too many dances, please specify the search query')   # Telegram throws 414 error for message with too many button in it


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    try:
        send_res_msg(call.data, call.from_user.id)
    except Exception as e:
        logging.error(str(e))
        bot.send_message(call.from_user.id, 'An error accured, sorry, this dance seem to be broken')


def send_res_msg(danceid, chatid):
    dinfo, dcribs = get_data(danceid)
    dinfo_msg = dinfo[5] + "\n\nAuthor: " + dinfo[0] + "\nType: " + dinfo[1] + "\nSet: " + dinfo[2] + "\nCouples: " + dinfo[3]
    if dinfo[4]:  # Show Medley type in the dance is Medley
        dinfo_msg = dinfo_msg + "\nMedley: " + dinfo[4]
    for symb in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:  # Escape special characters in the description before applying markdown
        dinfo_msg = dinfo_msg.replace(symb, "\\%s" % symb)
    dinfo_msg = re.sub(r'(.*\n\n)', r'*\1*', dinfo_msg)
    bot.send_message(chatid, dinfo_msg, parse_mode='MarkdownV2')
    bot.send_message(chatid, get_nice_crib(dcribs), parse_mode='MarkdownV2')
    png_url = get_image(str(danceid))
    if png_url:
        try:
            bot.send_photo(chatid, png_url)
        except Exception as e:
            bot.send_message(chatid, 'The diagramm exists, but cannot be displayed')
            logging.error(str(e) + "; Diagramm url: " + png_url)
    qi_result = open(QIpath + 'QI_result', 'a')
    qi_result.write(str(datetime.now()) + ' : ' + dinfo[5] + '\n')
    qi_result.close()


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
    cursor.execute("PRAGMA read_committed = true;")
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
    if dtype[0][1] == 4:
        medley = cursor.execute(medley_query).fetchall()[0][0]
    dset = cursor.execute(set_query).fetchall()
    dcpls = cursor.execute(cpls_query).fetchall()
    dname = cursor.execute(dname_query).fetchall()
    # Replace empty values with N/A
    # ---------------------------------------------------#
    if len(dset):
        fset = dset[0][0]
    else:
        fset = "N/A"
    if len(dcpls):
        fcpls = dcpls[0][0]
    else:
        fcpls = "N/A"
    if len(dauthor):
        fauthor = dauthor[0][0]
    else:
        fauthor = "N/A"
    if len(dtype):
        ftype = dtype[0][0]
    else:
        ftype = "N/A"
    # ---------------------------------------------------#
    dance_info = (fauthor, ftype, fset, fcpls, medley, dname[0][0])
    i = 0
    for row in dancelist:  # ---------Concatenating crib texts and crib sources to one list
        cribs.append((cribsources[i][0], row[1]))
        i = i + 1
    return dance_info, cribs


def get_image(danceid):
    png_url = "https://my.strathspey.org/dd/diagram/%s/" + str(danceid) + "/?f=png&w=800"
    for ctype in ['kr', 'scddb']:
        request = requests.get(png_url % ctype)
        if request.status_code == 200:
            return png_url % ctype
    return False


def get_crib(cribs):
    if not cribs:
        return 'No cribs available'
    i = 0
    for row in cribs:
        if row[i][0] == 'E-cribs':
            return "Source: " + row[0] + '\n\n' + row[1]
        if row[i][0] == 'MiniCribs':
            return "Source: " + row[0] + '\n\n' + row[1]
        else:
            return "Source: " + row[0] + '\n\n' + row[1]


#  Escape special symbols to appl markdown, make bars number and durations bold
def get_nice_crib(cribs):
    crib = get_crib(cribs)
    for symb in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        crib = crib.replace(symb, "\\%s" % symb)
    crib = re.sub(r'([0-9].*::)(.*)', r'*\1*\2', crib)
    crib = re.sub(r'(\\\_while\\\_\\\{[0-9]*\\\})', r'*\1*', crib)
    crib = re.sub(r'(\\\_while\\\{[0-9]*\\\}\\\_)', r'*\1*', crib)
    return crib


bot.polling(True)
