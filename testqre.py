import telebot
import sqlite3
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging
import sys

scddata = '/opt/scdsearchbot/scddata-2.0.sql'
name = 'Strip'

danceid = '6359'

connection = sqlite3.connect(":memory:")
cursor = connection.cursor()
sql_file = open(scddata)
sql_as_string = sql_file.read()
cursor.executescript(sql_as_string)
result = []
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
    src_list = src_list + str(row[0]) + ','
    cribs.append(str(row[1]))
cribsources = cursor.execute(cribsrc_query % (src_list[:-1])).fetchall()
dauthor = cursor.execute(author_query).fetchall()
dtype = cursor.execute(type_query).fetchall()
dset = cursor.execute(set_query).fetchall()
dcpls = cursor.execute(cpls_query).fetchall()

result = (dauthor[0][0], dtype[0][0], dset[0][0], dcpls[0][0])
i = 0
for row in dancelist:
    cribs.append((cribsources[i][0], row[1]))
    i = i + 1
print(cribs)