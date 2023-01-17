# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import MySQLdb
import asyncio, aiomysql
import json, os, time, copy
import traceback, threading

from app import app, config, version

host = config.mysql_host
user = config.mysql_user
passwd = config.mysql_passwd
dbname = config.mysql_db
conn = MySQLdb.connect(host = host, user = user, passwd = passwd, db = dbname)
cur = conn.cursor()

# NOTE DATA DIRECTORY requires FILE privilege, which does not seems to be included in ALL 

cur.execute(f"CREATE TABLE IF NOT EXISTS user (userid INT, discordid BIGINT UNSIGNED, name TEXT, avatar TEXT, bio TEXT, \
    email TEXT, truckersmpid BIGINT, steamid BIGINT, roles TEXT, join_timestamp BIGINT, mfa_secret VARCHAR(16))")
cur.execute(f"CREATE TABLE IF NOT EXISTS user_password (discordid BIGINT UNSIGNED, email TEXT, password TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS user_activity (discordid BIGINT UNSIGNED, activity TEXT, timestamp BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS user_notification (notificationid INT, discordid BIGINT UNSIGNED, content TEXT, \
    timestamp BIGINT, status INT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS banned (discordid BIGINT UNSIGNED, expire_timestamp BIGINT, reason TEXT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS mythpoint (userid INT, point INT, timestamp BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS dlog (logid INT, userid INT, data MEDIUMTEXT, topspeed FLOAT, timestamp BIGINT, \
    isdelivered INT, profit DOUBLE, unit INT, fuel DOUBLE, distance DOUBLE, navioid BIGINT) DATA DIRECTORY = '{config.mysql_ext}'")
# unit = 1: euro | 2: dollar

cur.execute(f"CREATE TABLE IF NOT EXISTS telemetry (logid BIGINT, uuid TEXT, userid INT, data MEDIUMTEXT) DATA DIRECTORY = '{config.mysql_ext}'")
cur.execute(f"CREATE TABLE IF NOT EXISTS temptelemetry (steamid BIGINT, uuid CHAR(36), game INT, x INT, y INT, z INT, mods TEXT, timestamp BIGINT) DATA DIRECTORY = '{config.mysql_ext}'")

cur.execute(f"CREATE TABLE IF NOT EXISTS announcement (announcementid INT, userid INT, title TEXT, content TEXT, \
    announcement_type INT, timestamp BIGINT, is_private INT) DATA DIRECTORY = '{config.mysql_ext}'")
# atype = 0: info | 1: event | 2: warning | 3: critical

cur.execute(f"CREATE TABLE IF NOT EXISTS application (applicationid INT, application_type INT, discordid BIGINT UNSIGNED, data TEXT,\
    status INT, submit_timestamp BIGINT, update_staff_userid INT, update_staff_timestamp BIGINT) DATA DIRECTORY = '{config.mysql_ext}'")
# status = 0: pending | 1: accepted | 2: declined

cur.execute(f"CREATE TABLE IF NOT EXISTS challenge (challengeid INT, userid INT, title TEXT, description TEXT, \
    start_time BIGINT, end_time BIGINT, challenge_type INT, delivery_count INT, required_roles TEXT, required_distance BIGINT, \
    reward_points INT, public_details INT, job_requirements TEXT) DATA DIRECTORY = '{config.mysql_ext}'")
cur.execute(f"CREATE TABLE IF NOT EXISTS challenge_record (userid INT, challengeid INT, logid INT, timestamp BIGINT) \
            DATA DIRECTORY = '{config.mysql_ext}'")
cur.execute(f"CREATE TABLE IF NOT EXISTS challenge_completed (userid INT, challengeid INT, points INT, timestamp BIGINT) \
            DATA DIRECTORY = '{config.mysql_ext}'")

cur.execute(f"CREATE TABLE IF NOT EXISTS division (logid INT, divisionid INT, userid INT, request_timestamp BIGINT, \
    status INT, update_timestamp BIGINT, update_staff_userid INT, message TEXT) DATA DIRECTORY = '{config.mysql_ext}'")
# status = 0: pending | 1: validated | 2: denied

cur.execute(f"CREATE TABLE IF NOT EXISTS downloads (downloadsid INT, userid INT, title TEXT, description TEXT, \
    link TEXT, orderid INT, click_count INT) DATA DIRECTORY = '{config.mysql_ext}'")
cur.execute(f"CREATE TABLE IF NOT EXISTS downloads_templink (downloadsid INT, secret CHAR(8), expire BIGINT) DATA DIRECTORY = '{config.mysql_ext}'")

cur.execute(f"CREATE TABLE IF NOT EXISTS event (eventid INT, userid INT, link TEXT, departure TEXT, destination TEXT, distance TEXT, \
    meetup_timestamp BIGINT, departure_timestamp BIGINT, description TEXT, is_private INT, title TEXT, attendee TEXT, points INT, vote TEXT) DATA DIRECTORY = '{config.mysql_ext}'")

cur.execute(f"CREATE TABLE IF NOT EXISTS session (token CHAR(36), discordid BIGINT UNSIGNED, timestamp BIGINT, ip TEXT, \
        country TEXT, user_agent TEXT, last_used_timestamp BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS ratelimit (ip TEXT, endpoint TEXT, first_request_timestamp BIGINT, request_count INT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS temp_identity_proof (token CHAR(36), discordid BIGINT UNSIGNED, expire BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS appsession (token CHAR(36), discordid BIGINT UNSIGNED, timestamp BIGINT)")
cur.execute(f"CREATE TABLE IF NOT EXISTS auditlog (userid INT, operation TEXT, timestamp BIGINT) DATA DIRECTORY = '{config.mysql_ext}'")
cur.execute(f"CREATE TABLE IF NOT EXISTS settings (discordid BIGINT UNSIGNED, skey TEXT, sval TEXT)")

cur.execute(f"SELECT skey FROM settings")
t = cur.fetchall()
keys = ["nxtuserid", "nxtlogid", "nxtappid", "nxtannid", "nxtchallengeid", "nxtdownloadsid", "nxteventid", "nxtnotificationid"]
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
"CREATE INDEX downloads_downloadsid ON downloads (downloadsid)",
"CREATE INDEX downloads_templink_secret ON downloads_templink (secret)",
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
cur.close()
conn.close()

# LEGACY MySQLdb
def genconn():
    conn = MySQLdb.connect(host = host, user = user, passwd = passwd, db = dbname)
    conn.ping()
    return conn

# ASYNCIO aiomysql
class AIOSQL:
    def __init__(self, host, user, passwd, dbname):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.dbname = dbname
        self.conns = {}
        self.pool = None
        self.shutdown_lock = False

    def release(self):
        conns = self.conns
        to_delete = []
        for tdhrid in conns.keys():
            (tconn, tcur, start_time, extra_time) = conns[tdhrid]
            if time.time() - start_time >= 1:
                to_delete.append(tdhrid)
                try:
                    self.pool.release(tconn)
                except:
                    traceback.print_exc()
                    pass
        for tdhrid in to_delete:
            del conns[tdhrid]
        self.conns = conns

    async def new_conn(self, dhrid, extra_time = 0):
        while self.shutdown_lock:
            await asyncio.sleep(0.1)

        if self.pool is None: # init pool
            self.pool = await aiomysql.create_pool(host = self.host, user = self.user, password = self.passwd, \
                                        db = self.dbname, autocommit = False, pool_recycle = 5)

        self.release()

        conn = await self.pool.acquire()
        cur = await conn.cursor()
        await cur.execute(f"SET wait_timeout={3+extra_time}, lock_wait_timeout=3;")
        conns = self.conns
        conns[dhrid] = [conn, cur, time.time() + extra_time, extra_time]
        self.conns = conns

        return conn

    async def create_pool(self):
        if self.pool is None: # init pool
            self.pool = await aiomysql.create_pool(host = self.host, user = self.user, password = self.passwd, \
                                        db = self.dbname, autocommit = False, pool_recycle = 5)

    async def shutdown(self):
        self.shutdown_lock = True
        self.pool.close()

    async def close_conn(self, dhrid):
        self.pool.release(self.conns[dhrid][0])
        del self.conns[dhrid]

    async def refresh(self, dhrid):
        conns = self.conns
        try:
            conns[dhrid][2] = time.time() + conns[dhrid][3]
        except:
            try:
                conn = await self.pool.acquire()
                cur = await conn.cursor()
                conns = self.conns
                conns[dhrid] = [conn, cur, time.time() + conns[dhrid][3], conns[dhrid][3]]
            except:
                pass
        self.conns = conns

    async def commit(self, dhrid):
        await self.refresh(dhrid)
        await self.conns[dhrid][0].commit()

    async def execute(self, dhrid, sql):
        await self.refresh(dhrid)
        await self.conns[dhrid][1].execute(sql)

    async def fetchone(self, dhrid):
        await self.refresh(dhrid)
        ret = await self.conns[dhrid][1].fetchone()
        return ret

    async def fetchall(self, dhrid):
        await self.refresh(dhrid)
        ret = await self.conns[dhrid][1].fetchall()
        return ret

aiosql = AIOSQL(host = host, user = user, passwd = passwd, dbname = dbname)