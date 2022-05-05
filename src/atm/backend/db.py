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
cur.execute(f"CREATE TABLE IF NOT EXISTS auditlog (memberid INT, operation TEXT, timestamp BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS member (memberid INT, name TEXT, avatar TEXT, discordid BIGINT, email TEXT, \
    roles TEXT, joints BIGINT, truckersmpid BIGINT, steamid BIGINT, extra TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS application (applicationid BIGINT, apptype INT, discordid BIGINT, truckersmpid BIGINT, steamid BIGINT, data TEXT, status INT, closedBy BIGINT, closedTimestamp BIGINT)")
# status = 0: pending | 1: accepted | 2: declined
cur.execute(f"CREATE TABLE IF NOT EXISTS user (discordid BIGINT, discordname TEXT, email TEXT, data TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS session (token CHAR(36), discordid BIGINT, timestamp BIGINT)")
conn.commit()
"""
CREATE INDEX auditlog_memberid ON auditlog (memberid);
CREATE INDEX auditlog_timestamp ON auditlog (timestamp);
CREATE INDEX member_memberid ON member (memberid);
CREATE INDEX member_discordid ON member (discordid);
CREATE INDEX application_applicationid ON application (applicationid);
CREATE INDEX application_discordid ON application (discordid);
CREATE INDEX application_truckersmpid ON application (truckersmpid);
CREATE INDEX user_discordid ON user (discordid);
CREATE INDEX session_discordid ON session (discordid);
CREATE INDEX session_token ON session (token);
"""
del cur

def newconn():
    conn = MySQLdb.connect(host = host, user = user, passwd = passwd, db = dbname)
    conn.ping()
    return conn