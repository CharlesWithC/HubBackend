# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import time
import warnings

import aiomysql
import pymysql

from logger import logger


def init(app):
    conn = pymysql.connect(host = app.config.mysql_host, user = app.config.mysql_user, passwd = app.config.mysql_passwd, db = app.config.mysql_db)
    cur = conn.cursor()

    # NOTE DATA DIRECTORY requires FILE privilege, which does not seems to be included in ALL

    cur.execute("CREATE TABLE IF NOT EXISTS user (uid INT AUTO_INCREMENT PRIMARY KEY, userid INT, name TEXT, email TEXT, avatar TEXT, bio TEXT, roles TEXT, discordid BIGINT UNSIGNED, steamid BIGINT UNSIGNED, truckersmpid BIGINT UNSIGNED, join_timestamp BIGINT, mfa_secret VARCHAR(16))")
    cur.execute("CREATE TABLE IF NOT EXISTS discord_access_token (discordid BIGINT UNSIGNED, callback_url TEXT, access_token TEXT, refresh_token TEXT, expire_timestamp BIGINT)") # source is callback|connect
    # uid is unique identifier, userid is actually member id
    cur.execute("CREATE TABLE IF NOT EXISTS user_password (uid INT, email TEXT, password TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS user_activity (uid INT, activity TEXT, timestamp BIGINT)")
    cur.execute("CREATE TABLE IF NOT EXISTS user_notification (notificationid INT AUTO_INCREMENT PRIMARY KEY, uid INT, content TEXT, timestamp BIGINT, status INT)")
    cur.execute("CREATE TABLE IF NOT EXISTS user_role_history (historyid INT AUTO_INCREMENT PRIMARY KEY, uid INT, added_roles TEXT, removed_roles TEXT, timestamp BIGINT)")
    cur.execute("CREATE TABLE IF NOT EXISTS banned (uid INT, email TEXT, discordid BIGINT UNSIGNED, steamid BIGINT UNSIGNED, truckersmpid BIGINT UNSIGNED, expire_timestamp BIGINT, reason TEXT)")
    # Either ID / email matched will result a block on login / signup, or an automatic ban on new account registered with a new email that is being connected to banned discord / steam.
    cur.execute("CREATE TABLE IF NOT EXISTS pending_user_deletion (uid INT, expire_timestamp BIGINT, status INT)")

    cur.execute("CREATE TABLE IF NOT EXISTS bonus_point (userid INT, point INT, timestamp BIGINT)")
    cur.execute(f"CREATE TABLE IF NOT EXISTS dlog (logid INT AUTO_INCREMENT, userid INT, data MEDIUMTEXT, topspeed FLOAT, timestamp BIGINT, isdelivered INT, profit DOUBLE, unit INT, fuel DOUBLE, distance DOUBLE, trackerid BIGINT, tracker_type INT, view_count INT, KEY dlog_logid (logid)) DATA DIRECTORY = '{app.config.mysql_ext}'")
    # unit = 1: euro | 2: dollar
    cur.execute("CREATE TABLE IF NOT EXISTS dlog_stats (item_type INT, userid INT, item_key TEXT, item_name TEXT, count BIGINT, sum BIGINT)")
    # item_type = 1: truck | 2: trailer | 3: plate_country | 4: cargo | 5: cargo_market | 6: source_city | 7: source_company | 8: destination_city | 9: destination_company | 10: fine | 11: speeding | 12: tollgate | 13: ferry | 14: train | 15: collision | 16: teleport
    # userid = >=0: user id | -1: company overall stats
    # count => number of events
    # sum => sum of meta data in event (only for (10,12,13,14))

    cur.execute(f"CREATE TABLE IF NOT EXISTS telemetry (logid BIGINT, uuid TEXT, userid INT, data MEDIUMTEXT) DATA DIRECTORY = '{app.config.mysql_ext}'")

    cur.execute(f"CREATE TABLE IF NOT EXISTS announcement (announcementid INT AUTO_INCREMENT PRIMARY KEY, userid INT, title TEXT, content TEXT, announcement_type INT, timestamp BIGINT, is_private INT, order_id INT, is_pinned INT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    # atype = 0: info | 1: event | 2: warning | 3: critical

    cur.execute(f"CREATE TABLE IF NOT EXISTS application (applicationid INT AUTO_INCREMENT PRIMARY KEY, application_type INT, uid INT, data TEXT,status INT, submit_timestamp BIGINT, update_staff_userid INT, update_staff_timestamp BIGINT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    # status = 0: pending | 1: accepted | 2: declined

    cur.execute(f"CREATE TABLE IF NOT EXISTS challenge (challengeid INT AUTO_INCREMENT PRIMARY KEY, userid INT, title TEXT, description TEXT, start_time BIGINT, end_time BIGINT, challenge_type INT, orderid INT, is_pinned INT, delivery_count INT, required_roles TEXT, required_distance BIGINT, reward_points INT, public_details INT, job_requirements TEXT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    cur.execute(f"CREATE TABLE IF NOT EXISTS challenge_record (userid INT, challengeid INT, logid INT, timestamp BIGINT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    cur.execute(f"CREATE TABLE IF NOT EXISTS challenge_completed (userid INT, challengeid INT, points INT, timestamp BIGINT) DATA DIRECTORY = '{app.config.mysql_ext}'")

    cur.execute(f"CREATE TABLE IF NOT EXISTS division (logid INT, divisionid INT, userid INT, request_timestamp BIGINT, status INT, update_timestamp BIGINT, update_staff_userid INT, message TEXT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    # status = 0: pending | 1: validated | 2: denied

    cur.execute(f"CREATE TABLE IF NOT EXISTS downloads (downloadsid INT AUTO_INCREMENT PRIMARY KEY, userid INT, title TEXT, description TEXT, link TEXT, orderid INT, is_pinned INT, click_count INT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    cur.execute(f"CREATE TABLE IF NOT EXISTS downloads_templink (downloadsid INT, secret CHAR(8), expire BIGINT) DATA DIRECTORY = '{app.config.mysql_ext}'")

    cur.execute("CREATE TABLE IF NOT EXISTS economy_balance (userid INT, balance BIGINT)")
    cur.execute(f"CREATE TABLE IF NOT EXISTS economy_truck (vehicleid INT AUTO_INCREMENT PRIMARY KEY, truckid TEXT, garageid TEXT, slotid INT, userid INT, assigneeid INT, price BIGINT UNSIGNED, income BIGINT, service_cost BIGINT, odometer BIGINT UNSIGNED, damage FLOAT, purchase_timestamp BIGINT, status INT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    # NOTE damage is a percentage (e.g. 0.01 => 1%)
    cur.execute(f"CREATE TABLE IF NOT EXISTS economy_garage (slotid INT AUTO_INCREMENT PRIMARY KEY, garageid TEXT, userid INT, price BIGINT UNSIGNED, note TEXT, purchase_timestamp BIGINT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    cur.execute(f"CREATE TABLE IF NOT EXISTS economy_merch (itemid INT AUTO_INCREMENT PRIMARY KEY, merchid TEXT, userid INT, buy_price BIGINT UNSIGNED, sell_price BIGINT UNSIGNED, purchase_timestamp BIGINT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    cur.execute(f"CREATE TABLE IF NOT EXISTS economy_transaction (txid INT AUTO_INCREMENT PRIMARY KEY, from_userid INT, to_userid INT, amount BIGINT, note TEXT, message TEXT, from_new_balance BIGINT, to_new_balance BIGINT, timestamp BIGINT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    # userid = -1000 => company account
    # userid = -1001 => dealership
    # userid = -1002 => garage agency
    # userid = -1003 => client
    # userid = -1004 => service station
    # userid = -1005 => scrap station
    # userid = -1006 => blackhole

    cur.execute(f"CREATE TABLE IF NOT EXISTS event (eventid INT AUTO_INCREMENT PRIMARY KEY, userid INT, link TEXT, departure TEXT, destination TEXT, distance TEXT, meetup_timestamp BIGINT, departure_timestamp BIGINT, description TEXT, is_private INT, title TEXT, attendee TEXT, points INT, vote TEXT) DATA DIRECTORY = '{app.config.mysql_ext}'")

    cur.execute("CREATE TABLE IF NOT EXISTS session (token CHAR(36), uid INT, timestamp BIGINT, ip TEXT, country TEXT, user_agent TEXT, last_used_timestamp BIGINT)")
    cur.execute("CREATE TABLE IF NOT EXISTS ratelimit (identifier TEXT, endpoint TEXT, first_request_timestamp BIGINT, request_count INT)")
    cur.execute("CREATE TABLE IF NOT EXISTS auth_ticket (token CHAR(36), uid BIGINT UNSIGNED, expire BIGINT)")
    cur.execute("CREATE TABLE IF NOT EXISTS application_token (app_name TEXT, token CHAR(36), uid BIGINT UNSIGNED, timestamp BIGINT, last_used_timestamp BIGINT)")
    cur.execute("CREATE TABLE IF NOT EXISTS email_confirmation (uid INT, secret TEXT, operation TEXT, expire BIGINT)")
    cur.execute(f"CREATE TABLE IF NOT EXISTS auditlog (uid INT, operation TEXT, timestamp BIGINT) DATA DIRECTORY = '{app.config.mysql_ext}'")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (uid BIGINT UNSIGNED, skey TEXT, sval TEXT)")

    cur.execute("SELECT skey FROM settings")
    t = cur.fetchall()
    keys = ["nxtuserid", "dlog_stats_up_to"]
    for key in keys:
        if (key,) not in t:
            cur.execute(f"INSERT INTO settings VALUES (NULL, '{key}', 1)")
    if ("version",) not in t:
        cur.execute(f"INSERT INTO settings VALUES (NULL, 'version', '{app.version}')")

    indexes = ["CREATE INDEX user_uid ON user (uid)",
    "CREATE INDEX user_userid ON user (userid)",
    "CREATE INDEX user_discordid ON user (discordid)",
    "CREATE INDEX user_truckersmpid ON user (truckersmpid)",
    "CREATE INDEX user_steamid ON user (steamid)",

    "CREATE INDEX user_role_history_userid ON user_role_history (userid)",
    "CREATE INDEX user_activity_uid ON user_activity (uid)",
    "CREATE INDEX user_password_uid ON user_password (uid)",
    "CREATE INDEX user_password_email ON user_password (email)",
    "CREATE INDEX pending_user_deletion_uid ON pending_user_deletion (uid)",
    "CREATE INDEX pending_user_deletion_expire_timestamp ON pending_user_deletion (expire_timestamp)",

    "CREATE INDEX banned_uid ON banned (uid)",
    "CREATE INDEX banned_discordid ON banned (discordid)",
    "CREATE INDEX banned_steamid ON banned (steamid)",
    "CREATE INDEX banned_expire_timestamp ON banned (expire_timestamp)",

    "CREATE INDEX bonus_point_userid ON bonus_point (userid)",
    "CREATE INDEX bonus_point_timestamp ON bonus_point (timestamp)",

    "CREATE INDEX dlog_logid ON dlog (logid)",
    "CREATE INDEX dlog_userid ON dlog (userid)",
    "CREATE INDEX dlog_trackerid ON dlog (trackerid)",
    "CREATE INDEX dlog_topspeed ON dlog (topspeed)",
    "CREATE INDEX dlog_distance ON dlog (distance)",
    "CREATE INDEX dlog_fuel ON dlog (fuel)",
    "CREATE INDEX dlog_unit ON dlog (unit)",
    "CREATE INDEX dlog_isdelivered ON dlog (isdelivered)",
    "CREATE INDEX dlog_timestamp ON dlog (timestamp)",

    "CREATE INDEX dlog_stats_item_type ON dlog_stats (item_type)",
    "CREATE INDEX dlog_stats_userid ON dlog_stats (userid)",
    "CREATE INDEX dlog_stats_count ON dlog_stats (count)",
    "CREATE INDEX dlog_stats_sum ON dlog_stats (sum)",

    "CREATE INDEX telemetry_logid ON telemetry (logid)",

    "CREATE INDEX division_logid ON division (logid)",
    "CREATE INDEX division_userid ON division (userid)",
    "CREATE INDEX division_divisionid ON division (divisionid)",

    "CREATE INDEX announcement_announcementid ON announcement (announcementid)",

    "CREATE INDEX application_applicationid ON application (applicationid)",
    "CREATE INDEX application_uid ON application (uid)",

    "CREATE INDEX downloads_downloadsid ON downloads (downloadsid)",
    "CREATE INDEX downloads_templink_secret ON downloads_templink (secret)",

    "CREATE INDEX economy_balance_userid ON economy_balance (userid)",
    "CREATE INDEX economy_balance_balance ON economy_balance (balance)",
    "CREATE INDEX economy_truck_vehicleid ON economy_truck (vehicleid)",
    "CREATE INDEX economy_truck_truckid ON economy_truck (truckid)",
    "CREATE INDEX economy_truck_slotid ON economy_truck (slotid)",
    "CREATE INDEX economy_truck_garageid ON economy_truck (garageid)",
    "CREATE INDEX economy_truck_userid ON economy_truck (userid)",
    "CREATE INDEX economy_garage_slotid ON economy_garage (slotid)",
    "CREATE INDEX economy_garage_garageid ON economy_garage (garageid)",
    "CREATE INDEX economy_garage_userid ON economy_garage (userid)",
    "CREATE INDEX economy_merch_ownid ON economy_merch (ownid)",
    "CREATE INDEX economy_merch_merchid ON economy_merch (merchid)",
    "CREATE INDEX economy_merch_userid ON economy_merch (userid)",
    "CREATE INDEX economy_transaction_txid ON economy_transaction (txid)",
    "CREATE INDEX economy_transaction_from_userid ON economy_transaction (from_userid)",
    "CREATE INDEX economy_transaction_to_userid ON economy_transaction (to_userid)",
    "CREATE INDEX economy_transaction_note ON economy_transaction (note)",

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
    "CREATE INDEX auth_ticket_token ON auth_ticket (token)",
    "CREATE INDEX application_token_token ON application_token (token)",
    "CREATE INDEX ratelimit_ip ON ratelimit (ip)",
    "CREATE INDEX email_confirmation_uid ON email_confirmation (uid)",
    "CREATE INDEX email_confirmation_secret ON email_confirmation (secret)",
    "CREATE INDEX auditlog_userid ON auditlog (userid)",
    "CREATE INDEX settings_uid ON settings (uid)"]

    for idx in indexes:
        try:
            cur.execute(idx)
        except:
            pass

    conn.commit()
    cur.close()
    conn.close()

# LEGACY non-async
def genconn(app, autocommit = False):
    conn = pymysql.connect(host = app.config.mysql_host, user = app.config.mysql_user, passwd = app.config.mysql_passwd, db = app.config.mysql_db, autocommit = autocommit)
    conn.ping()
    return conn

# ASYNCIO aiomysql
class aiosql:
    def __init__(self, app, host, user, passwd, db):
        self.app = app
        self.host = host
        self.user = user
        self.passwd = passwd
        self.db = db
        self.conns = {}
        self.pool = None
        self.shutdown_lock = False
        self.POOL_START_TIME = 0

    async def create_pool(self):
        if self.pool is None: # init pool
            self.pool = await aiomysql.create_pool(host = self.host, user = self.user, password = self.passwd, \
                                        db = self.db, autocommit = False, pool_recycle = 5, \
                                        maxsize = min(20, self.app.config.mysql_pool_size))
            self.POOL_START_TIME = time.time()

    def close_pool(self):
        self.shutdown_lock = True
        self.POOL_START_TIME = 0
        self.pool.terminate()

    async def restart_pool(self):
        self.POOL_START_TIME = 0
        self.pool.terminate()
        self.pool = await aiomysql.create_pool(host = self.host, user = self.user, password = self.passwd, \
                                        db = self.db, autocommit = False, pool_recycle = 5, \
                                        maxsize = min(20, self.app.config.mysql_pool_size))
        self.POOL_START_TIME = time.time()

    def release(self):
        conns = self.conns
        to_delete = []
        for tdhrid in conns.keys():
            (tconn, tcur, expire_time, extra_time) = conns[tdhrid]
            if time.time() - expire_time >= 2:
                to_delete.append(tdhrid)
                try:
                    self.pool.release(tconn)
                except Exception as exc:
                    logger.warning(f"Failed to release connection ({tdhrid}): {str(exc)}")
        for tdhrid in to_delete:
            del conns[tdhrid]
        self.conns = conns

    async def new_conn(self, dhrid, extra_time = 0):
        while self.shutdown_lock:
            raise pymysql.err.OperationalError("[aiosql] Shutting down in progress")

        if self.pool is None: # init pool
            self.pool = await aiomysql.create_pool(host = self.host, user = self.user, password = self.passwd, \
                                        db = self.db, autocommit = False, pool_recycle = 5, \
                                        maxsize = min(20, self.app.config.mysql_pool_size))
            self.POOL_START_TIME = time.time()

        self.release()

        try:
            try:
                conn = await asyncio.wait_for(self.pool.acquire(), timeout=3)
            except asyncio.TimeoutError:
                raise pymysql.err.OperationalError("[aiosql] Timeout")
            cur = await conn.cursor()
            await cur.execute("SET lock_wait_timeout=5;")
            conns = self.conns
            conns[dhrid] = [conn, cur, time.time() + extra_time, extra_time]
            self.conns = conns
            return conn
        except Exception as exc:
            raise pymysql.err.OperationalError(f"[aiosql] Failed to create connection ({dhrid}): {str(exc)}")

    async def refresh_conn(self, dhrid, extend = False):
        while self.shutdown_lock:
            raise pymysql.err.OperationalError("[aiosql] Shutting down")

        conns = self.conns
        try:
            conns[dhrid][2] = time.time() + conns[dhrid][3]
            cur = conns[dhrid][1]
            if extend:
                await cur.execute("SET lock_wait_timeout=5;")
        except:
            try:
                conn = await self.pool.acquire()
                cur = await conn.cursor()
                conns = self.conns
                conns[dhrid] = [conn, cur, time.time() + conns[dhrid][3], conns[dhrid][3]]
                if extend:
                    await cur.execute("SET lock_wait_timeout=5;")
            except:
                pass
        self.conns = conns

    async def extend_conn(self, dhrid, seconds):
        if dhrid not in self.conns.keys():
            return
        conns = self.conns
        try:
            conns[dhrid][2] = time.time() + seconds + 2
            conns[dhrid][3] = seconds + 2
        except:
            pass
        self.conns = conns
        await self.refresh_conn(dhrid, extend = True)

    async def close_conn(self, dhrid):
        if dhrid in self.conns.keys():
            try:
                self.pool.release(self.conns[dhrid][0])
            except:
                pass
            del self.conns[dhrid]

    async def commit(self, dhrid):
        await self.refresh_conn(dhrid)
        if dhrid in self.conns.keys():
            await self.conns[dhrid][0].commit()
        else:
            raise pymysql.err.OperationalError(f"[aiosql] Connection does not exist in pool ({dhrid})")

    async def execute(self, dhrid, sql):
        await self.refresh_conn(dhrid)
        if dhrid in self.conns.keys():
            with warnings.catch_warnings(record=True) as w:
                await self.conns[dhrid][1].execute(sql)
                if w:
                    logger.warning(f"DATABASE WARNING: {w[0].message}\nOn Execute: {sql}")
        else:
            raise pymysql.err.OperationalError(f"[aiosql] Connection does not exist in pool ({dhrid})")

    async def fetchone(self, dhrid):
        await self.refresh_conn(dhrid)
        if dhrid in self.conns.keys():
            return await self.conns[dhrid][1].fetchone()
        else:
            raise pymysql.err.OperationalError(f"[aiosql] Connection does not exist in pool ({dhrid})")

    async def fetchall(self, dhrid):
        await self.refresh_conn(dhrid)
        if dhrid in self.conns.keys():
            return await self.conns[dhrid][1].fetchall()
        else:
            raise pymysql.err.OperationalError(f"[aiosql] Connection does not exist in pool ({dhrid})")
