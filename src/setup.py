# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
from getpass import getpass

import bcrypt

import db
from db import genconn
from functions import *


def create_user(config, email: str, password: str):
    conn = genconn(config)
    cur = conn.cursor()

    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwdhash = bcrypt.hashpw(password, salt).decode()
    email = convertQuotation(email)

    try:
        cur.execute(f"SELECT uid FROM user WHERE email = '{email}'")
        t = cur.fetchall()
        if len(t) != 0:
            return "Email is taken by another user."

        cur.execute(f"INSERT INTO user(userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, join_timestamp, mfa_secret, tracker_in_use) VALUES (-1, '{email}', '{email}', '', '', '', NULL, NULL, NULL, {int(time.time())}, '', 0)")
        cur.execute("SELECT LAST_INSERT_ID();")
        uid = cur.fetchone()[0]
        cur.execute(f"DELETE FROM user_password WHERE email = '{email}'")
        cur.execute(f"INSERT INTO user_password VALUES ({uid}, '{email}', '{b64e(pwdhash)}')")
        conn.commit()

        return uid
    except Exception as exc:
        return exc
    finally:
        cur.close()
        conn.close()

def accept_user(config, uid: int):
    conn = genconn(config)
    cur = conn.cursor()

    try:
        cur.execute(f"SELECT userid FROM user WHERE uid = {uid}")
        t = cur.fetchall()
        if len(t) == 0:
            return "User does not exist."
        if t[0][0] >= 0:
            return "User is already accepted as member."

        cur.execute("SELECT sval FROM settings WHERE skey = 'nxtuserid' FOR UPDATE")
        t = cur.fetchone()
        userid = int(t[0])

        cur.execute(f"UPDATE user SET userid = {userid}, join_timestamp = {int(time.time())} WHERE uid = {uid}")
        cur.execute(f"UPDATE settings SET sval = {userid+1} WHERE skey = 'nxtuserid'")
        conn.commit()

        return userid
    except Exception as exc:
        return exc
    finally:
        cur.close()
        conn.close()

def update_roles(config, userid: int, roles: list[int]):
    conn = genconn(config)
    cur = conn.cursor()

    try:
        cur.execute(f"SELECT userid FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        if len(t) == 0 or userid < 0:
            return "User does not exist."

        cur.execute(f"UPDATE user SET roles = {list2str(roles)} WHERE userid = {userid}")
        conn.commit()

        return True
    except Exception as exc:
        return exc
    finally:
        cur.close()
        conn.close()

def handle_commands(config, args):
    if args.subcommand == "init-db":
        db.init(config, version)
        print("Database initialized.")

    elif args.subcommand == "create-user":
        password = getpass("Enter password: ")
        result = create_user(config, args.email, password)
        if isint(result):
            print(f"Created user with UID {result}.")
        else:
            print(f"Unable to create user: {result}")

    elif args.subcommand == "accept-user":
        result = accept_user(config, args.uid)
        if isint(result):
            print(f"Accepted user {args.uid} as member with user id {result}.")
        else:
            print(f"Unable to accept user as member: {result}")

    elif args.subcommand == "update-roles":
        result = update_roles(config, args.userid, args.roles)
        if result is True:
            print(f"Updated user {args.userid} roles to {args.roles}.")
        else:
            print(f"Unable to update roles: {result}")
