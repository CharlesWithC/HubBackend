# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

import MySQLdb
import json, os

from app import app, config, version

host = config.mysql_host
user = config.mysql_user
passwd = config.mysql_passwd
dbname = config.mysql_db
conn = MySQLdb.connect(host = host, user = user, passwd = passwd, db = dbname)
cur = conn.cursor()

# NOTE DATA DIRECTORY requires FILE privilege, which does not seems to be included in ALL 

cur.execute(f"CREATE TABLE IF NOT EXISTS user (userid INT, discordid BIGINT, name TEXT, avatar TEXT, bio TEXT, \
    email TEXT, truckersmpid BIGINT, steamid BIGINT, roles TEXT, join_timestamp BIGINT, mfa_secret VARCHAR(16))")
cur.execute(f"CREATE TABLE IF NOT EXISTS user_password (discordid BIGINT, email TEXT, password TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS user_activity (discordid BIGINT, activity TEXT, timestamp BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS user_notification (notificationid INT, discordid BIGINT, content TEXT, \
    timestamp BIGINT, status INT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS banned (discordid BIGINT, expire_timestamp BIGINT, reason TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS mythpoint (userid INT, point INT, timestamp INT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS dlog (logid INT, userid INT, data MEDIUMTEXT, topspeed FLOAT, timestamp BIGINT, \
    isdelivered INT, profit DOUBLE, unit INT, fuel DOUBLE, distance DOUBLE, navioid BIGINT) DATA DIRECTORY = '{config.mysql_ext}'")
# unit = 1: euro | 2: dollar

cur.execute(f"CREATE TABLE IF NOT EXISTS telemetry (logid BIGINT, uuid TEXT, userid INT, data MEDIUMTEXT) DATA DIRECTORY = '{config.mysql_ext}'")
cur.execute(f"CREATE TABLE IF NOT EXISTS temptelemetry (steamid BIGINT, uuid CHAR(36), game INT, x INT, y INT, z INT, mods TEXT, timestamp BIGINT) DATA DIRECTORY = '{config.mysql_ext}'")

cur.execute(f"CREATE TABLE IF NOT EXISTS announcement (announcementid INT, userid INT, title TEXT, content TEXT, \
    announcement_type INT, timestamp BIGINT, is_private INT) DATA DIRECTORY = '{config.mysql_ext}'")
# atype = 0: info | 1: event | 2: warning | 3: critical

cur.execute(f"CREATE TABLE IF NOT EXISTS application (applicationid INT, application_type INT, discordid BIGINT, data TEXT,\
    status INT, submit_timestamp BIGINT, update_staff_userid INT, update_staff_timestamp BIGINT) DATA DIRECTORY = '{config.mysql_ext}'")
# status = 0: pending | 1: accepted | 2: declined

cur.execute(f"CREATE TABLE IF NOT EXISTS challenge (challengeid INT, userid INT, title TEXT, description TEXT, \
    start_time BIGINT, end_time BIGINT, challenge_type INT, delivery_count INT, required_roles TEXT, required_distance BIGINT, \
    reward_points BIGINT, public_details INT, job_requirements TEXT) DATA DIRECTORY = '{config.mysql_ext}'")
cur.execute(f"CREATE TABLE IF NOT EXISTS challenge_record (userid INT, challengeid INT, logid INT, timestamp BIGINT) \
            DATA DIRECTORY = '{config.mysql_ext}'")
cur.execute(f"CREATE TABLE IF NOT EXISTS challenge_completed (userid INT, challengeid INT, points INT, timestamp BIGINT) \
            DATA DIRECTORY = '{config.mysql_ext}'")

cur.execute(f"CREATE TABLE IF NOT EXISTS division (logid INT, divisionid INT, userid INT, request_timestamp BIGINT, \
    status INT, update_timestamp BIGINT, update_staff_userid INT, message TEXT) DATA DIRECTORY = '{config.mysql_ext}'")
# status = 0: pending | 1: validated | 2: denied

cur.execute(f"CREATE TABLE IF NOT EXISTS downloads (data MEDIUMTEXT) DATA DIRECTORY = '{config.mysql_ext}'")

cur.execute(f"CREATE TABLE IF NOT EXISTS event (eventid INT, userid INT, link TEXT, departure TEXT, destination TEXT, distance TEXT, \
    meetup_timestamp BIGINT, departure_timestamp BIGINT, description TEXT, is_private INT, title TEXT, attendee TEXT, points INT, vote TEXT) DATA DIRECTORY = '{config.mysql_ext}'")

cur.execute(f"CREATE TABLE IF NOT EXISTS session (token CHAR(36), discordid BIGINT, timestamp BIGINT, ip TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS ratelimit (ip TEXT, endpoint TEXT, first_request_timestamp BIGINT, request_count INT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS temp_identity_proof (token CHAR(36), discordid BIGINT, expire BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS appsession (token CHAR(36), discordid BIGINT, timestamp BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS auditlog (userid INT, operation TEXT, timestamp BIGINT) DATA DIRECTORY = '{config.mysql_ext}'")
cur.execute(f"CREATE TABLE IF NOT EXISTS settings (discordid BIGINT, skey TEXT, sval TEXT)")

cur.execute(f"SELECT skey FROM settings")
t = cur.fetchall()
keys = ["nxtuserid", "nxtappid", "nxtannid", "nxtlogid", "nxteventid", "nxtchallengeid", "nxtnotificationid"]
for key in keys:
    if not (key,) in t:
        cur.execute(f"INSERT INTO settings VALUES (0, '{key}', 1)")
if not ("version",) in t:
    cur.execute(f"INSERT INTO settings VALUES (0, 'version', '{version}')")

indexes = ["CREATE INDEX user_userid ON user (userid)",
"CREATE INDEX user_discordid ON user (discordid)",
"CREATE INDEX user_truckersmpid ON user (truckersmpid)",
"CREATE INDEX user_steamid ON user (steamid)",
"CREATE INDEX user_activity_discordid ON user_activity (discordid)",
"CREATE INDEX user_password_discordid ON user_password (discordid)",
"CREATE INDEX user_password_email ON user_password (email)",
"CREATE INDEX banned_discordid ON banned (discordid)",
"CREATE INDEX banned_expire_timestamp ON banned (expire_timestamp)",
"CREATE INDEX mythpoint_idx ON banned (userid, timestamp)",
"CREATE INDEX dlog_logid ON dlog (logid)",
"CREATE INDEX dlog_userid ON dlog (userid)",
"CREATE INDEX dlog_navioid ON dlog (navioid)",
"CREATE INDEX dlog_topspeed ON dlog (topspeed)",
"CREATE INDEX telemetry_logid ON telemetry (logid)",
"CREATE INDEX temptelemetry_steamid ON temptelemetry (steamid)",
"CREATE INDEX temptelemetry_uuid ON temptelemetry (uuid)",
"CREATE INDEX division_logid ON division (logid)",
"CREATE INDEX division_userid ON division (userid)",
"CREATE INDEX division_divisionid ON division (divisionid)",
"CREATE INDEX announcement_announcementid ON announcement (announcementid)",
"CREATE INDEX application_applicationid ON application (applicationid)",
"CREATE INDEX application_discordid ON application (discordid)",
"CREATE INDEX event_eventid ON event (eventid)",
"CREATE INDEX challenge_challengeid ON challenge (challengeid)",
"CREATE INDEX challenge_start_time ON challenge (start_time)",
"CREATE INDEX challenge_end_time ON challenge (end_time)",
"CREATE INDEX challenge_type ON challenge (challenge_type)",
"CREATE INDEX challenge_record_userid ON challenge_record (userid)",
"CREATE INDEX challenge_record_challengeid ON challenge_record (challengeid)",
"CREATE INDEX challenge_completed_userid ON challenge_completed (userid)",
"CREATE INDEX challenge_completed_challengeid ON challenge_completed (challengeid)",
"CREATE INDEX session_token ON session (token)",
"CREATE INDEX temp_identity_proof_token ON temp_identity_proof (token)",
"CREATE INDEX appsession_token ON appsession (token)",
"CREATE INDEX ratelimit_ip ON ratelimit (ip)",
"CREATE INDEX auditlog_userid ON auditlog (userid)",
"CREATE INDEX settings_discordid ON settings (discordid)"]
for idx in indexes:
    try:
        cur.execute(idx)
    except:
        pass
    
conn.commit()
del cur

def newconn():
    conn = MySQLdb.connect(host = host, user = user, passwd = passwd, db = dbname)
    conn.ping()
    return conn