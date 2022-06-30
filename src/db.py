# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

import MySQLdb
from app import app, config_txt
import json, os

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
cur.execute(f"CREATE TABLE IF NOT EXISTS driver (userid INT, totjobs INT, distance DOUBLE, fuel DOUBLE, xp DOUBLE, eventpnt BIGINT, joints BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS dlog (logid INT, userid INT, data MEDIUMTEXT, topspeed FLOAT, timestamp BIGINT, \
    isdelivered INT, profit DOUBLE, unit INT, fuel DOUBLE, distance DOUBLE, navioid BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS division (logid INT, divisionid INT, userid INT, requestts BIGINT, status INT, updatets BIGINT, staffid INT, reason TEXT)")
# status = 0: pending | 1: validated | 2: denied
cur.execute(f"CREATE TABLE IF NOT EXISTS event (eventid INT, userid INT, tmplink TEXT, departure TEXT, destination TEXT, distance TEXT, \
    mts BIGINT, dts BIGINT, img TEXT, pvt INT, title TEXT, attendee TEXT, eventpnt INT, vote TEXT)")
# tmplink = '' -> private convoy | m/dts -> meetup/departure timestamp | img -> multiple link separated with ','
# unit = 1: euro | 2: dollar
cur.execute(f"CREATE TABLE IF NOT EXISTS session (token CHAR(36), discordid BIGINT, timestamp BIGINT, ip TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS appsession (token CHAR(36), discordid BIGINT, timestamp BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS banned (discordid BIGINT, expire BIGINT, reason TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS application (applicationid BIGINT, apptype INT, discordid BIGINT, data TEXT,\
    status INT, submitTimestamp BIGINT, closedBy BIGINT, closedTimestamp BIGINT)")
# status = 0: pending | 1: accepted | 2: declined
cur.execute(f"CREATE TABLE IF NOT EXISTS settings (discordid BIGINT, skey TEXT, sval TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS auditlog (userid INT, operation TEXT, timestamp BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS downloads (data MEDIUMTEXT)")

# NOTE DATA DIRECTORY requires FILE privilege, which does not seems to be included in ALL 
cur.execute(f"CREATE TABLE IF NOT EXISTS telemetry (logid BIGINT, uuid TEXT, userid BIGINT, data MEDIUMTEXT) DATA DIRECTORY = '{config['telemetry_innodb_dir']}'")
cur.execute(f"CREATE TABLE IF NOT EXISTS temptelemetry (steamid BIGINT, uuid CHAR(36), game BIGINT, x INT, y INT, z INT, mods TEXT, timestamp BIGINT) DATA DIRECTORY = '{config['telemetry_innodb_dir']}'")

cur.execute(f"CREATE TABLE IF NOT EXISTS ratelimit (ip TEXT, endpoint TEXT, firstop BIGINT, opcount INT)")

cur.execute(f"SELECT * FROM settings WHERE skey = 'nxtuserid'")
t = cur.fetchall()
if len(t) == 0:
    cur.execute(f"INSERT INTO settings VALUES (0, 'nxtuserid', 1)")
    cur.execute(f"INSERT INTO settings VALUES (0, 'nxtappid', 1)")
    cur.execute(f"INSERT INTO settings VALUES (0, 'nxtannid', 1)")
    cur.execute(f"INSERT INTO settings VALUES (0, 'nxtlogid', 1)")
    cur.execute(f"INSERT INTO settings VALUES (0, 'nxteventid', 1)")

conn.commit()

# NOTE Those index can only be created manually
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
CREATE INDEX dlog_navioid ON dlog (navioid);
CREATE INDEX dlog_topspeed ON dlog (topspeed);
CREATE INDEX division_logid ON division (logid);
CREATE INDEX division_divisionid ON division (divisionid);
CREATE INDEX event_eventid ON event (eventid);
CREATE INDEX telemetry_logid ON telemetry (logid);
CREATE INDEX telemetry_userid ON telemetry (userid);
CREATE INDEX temptelemetry_uuidid ON temptelemetry (uuid);
CREATE INDEX temptelemetry_steamid ON temptelemetry (steamid);
"""
del cur

def newconn():
    conn = MySQLdb.connect(host = host, user = user, passwd = passwd, db = dbname)
    conn.ping()
    return conn