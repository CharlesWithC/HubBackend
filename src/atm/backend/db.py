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
cur.execute(f"CREATE TABLE IF NOT EXISTS announcement (aid INT, userid INT, title TEXT, content TEXT, \
    atype INT, timestamp BIGINT, pvt BIGINT)")
# atype = 0: info | 1: event | 2: warning | 3: critical
cur.execute(f"CREATE TABLE IF NOT EXISTS user (userid INT, discordid BIGINT, name TEXT, avatar TEXT, bio TEXT,\
    email TEXT, truckersmpid BIGINT, steamid BIGINT, roles TEXT, joints BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS driver (userid INT, distance DOUBLE, revenue DOUBLE, fuel DOUBLE, xp DOUBLE)")
cur.execute(f"CREATE TABLE IF NOT EXISTS dlog (logid INT, userid INT, data MEDIUMTEXT, topspeed FLOAT, timestamp BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS session (token CHAR(36), discordid BIGINT, timestamp BIGINT, ip TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS banned (discordid BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS application (applicationid BIGINT, apptype INT, discordid BIGINT, data TEXT,\
     status INT, submitTimestamp BIGINT, closedBy BIGINT, closedTimestamp BIGINT)")
# status = 0: pending | 1: accepted | 2: declined
cur.execute(f"CREATE TABLE IF NOT EXISTS settings (discordid BIGINT, skey TEXT, sval TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS auditlog (userid INT, operation TEXT, timestamp BIGINT)")
conn.commit()
"""
CREATE INDEX user_userid ON user (userid);
CREATE INDEX user_discordid ON user (discordid);
CREATE INDEX auditlog_userid ON auditlog (userid);
CREATE INDEX application_applicationid ON application (applicationid);
CREATE INDEX application_discordid ON application (discordid);
CREATE INDEX session_token ON session (token);
CREATE INDEX banned_discordid ON banned (discordid);
CREATE INDEX settings_discordid ON settings (discordid);
CREATE INDEX driver_userid ON driver (userid);
CREATE INDEX dlog_logid ON dlog (logid);
CREATE INDEX dlog_userid ON dlog (userid);
CREATE INDEX dlog_topspeed ON dlog (topspeed);
"""
del cur

def newconn():
    conn = MySQLdb.connect(host = host, user = user, passwd = passwd, db = dbname)
    conn.ping()
    return conn