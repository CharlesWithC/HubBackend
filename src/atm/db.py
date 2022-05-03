# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

import MySQLdb
from app import app
import json, os

config_txt = open("./config.json","r").read()
config = json.loads(config_txt)
host = config["mysql_host"]
user = config["mysql_user"]
passwd = config["mysql_passwd"]
dbname = config["mysql_db"]
conn = MySQLdb.connect(host = host, user = user, passwd = passwd, db = dbname)
cur = conn.cursor()
cur.execute(f"CREATE TABLE IF NOT EXISTS session (token CHAR(36), discordid BIGINT, discordname TEXT, email TEXT, data TEXT)")
conn.commit()
del cur

def newconn():
    conn = MySQLdb.connect(host = host, user = user, passwd = passwd, db = dbname)
    conn.ping()
    return conn