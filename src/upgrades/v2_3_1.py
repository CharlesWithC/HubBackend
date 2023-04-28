# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from db import genconn


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    USERID_TABLES = ["user", "bonus_point", "dlog", "telemetry", "announcement", "application", "challenge", "challenge_record", "challenge_completed", "division", "downloads", "economy_balance", "economy_truck", "economy_garage", "event"]
    SPECIAL_USERID_TABLES = {"application": ["update_staff_userid"], "division": ["update_staff_userid"], "economy_transaction": ["from_userid", "to_userid"]}

    UID_TABLES = ["user", "user_password", "user_activity", "user_notification", "banned", "session", "auth_ticket", "application_token", "email_confirmation", "auditlog", "settings"]

    print("Fixing ultra-high User ID / UID...")
    print("Fetching highest User ID below 1000: ", end = '')
    cur.execute("SELECT MAX(userid) FROM user WHERE userid < 1000")
    max_userid = cur.fetchone()
    if max_userid is None:
        print("No user found, fix aborted.")
    else:
        max_userid = max_userid[0]
        if max_userid > 900:
            print("Highest user ID is above 900, fix aborted.")
        else:
            print(max_userid)
            print("Fetching User ID above 1000...")
            cur.execute("SELECT userid FROM user WHERE userid >= 1000")
            t = cur.fetchall()
            if len(t) == 0:
                print("No user ID is above 1000, fix aborted.")
            else:
                for tt in t:
                    userid = tt[0]
                    max_userid += 1
                    print(f"Changing User ID: {userid} to {max_userid}")
                    for TABLE in USERID_TABLES:
                        cur.execute(f"UPDATE {TABLE} SET userid = {max_userid} WHERE userid = {userid}")
                    for TABLE in SPECIAL_USERID_TABLES.keys():
                        for COLUMN in SPECIAL_USERID_TABLES[TABLE]:
                            cur.execute(f"UPDATE {TABLE} SET {COLUMN} = {max_userid} WHERE {COLUMN} = {userid}")
                print("Update settings...")
                cur.execute(f"UPDATE settings SET sval = '{max_userid + 1}' WHERE skey = 'nxtuserid'")
                conn.commit()

    print("Fixing ultra-high UID...")
    print("Fetching highest UID below 1000: ", end = '')
    cur.execute("SELECT MAX(uid) FROM user WHERE uid < 1000")
    max_uid = cur.fetchone()
    if max_uid is None:
        print("No user found, fix aborted.")
    else:
        max_uid = max_uid[0]
        if max_uid > 900:
            print("Highest UID is above 900, fix aborted.")
        else:
            print(max_uid)
            print("Fetching UID above 1000...")
            cur.execute("SELECT uid FROM user WHERE uid >= 1000")
            t = cur.fetchall()
            if len(t) == 0:
                print("No UID is above 1000, fix aborted.")
            else:
                for tt in t:
                    uid = tt[0]
                    max_uid += 1
                    print(f"Changing UID: {uid} to {max_uid}")
                    for TABLE in UID_TABLES:
                        cur.execute(f"UPDATE {TABLE} SET uid = {max_uid} WHERE uid = {uid}")
                print("Update AUTO INCREMENT app.config...")
                cur.execute(f"ALTER TABLE user AUTO_INCREMENT = {max_uid + 1}")
                conn.commit()

    cur.close()
    conn.close()
    
    print("Fix finished")