# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This upgrade adds the "tracker_in_use" column to "user" table
# And set the default value based on the "tracker" in app.config

from db import genconn


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    try:
        cur.execute("SELECT tracker_in_use FROM user LIMIT 1")
    except:
        print("Updating user TABLE")
        cur.execute("ALTER TABLE user ADD tracker_in_use INT AFTER mfa_secret")
        cur.execute("UPDATE user SET tracker_in_use = 0") # set a default value first
        if type(app.config.tracker) == str:
            # config not updated yet
            if app.config.tracker == "tracksim":
                cur.execute("UPDATE user SET tracker_in_use = 2 WHERE userid >= 0")
            elif app.config.tracker == "trucky":
                cur.execute("UPDATE user SET tracker_in_use = 3 WHERE userid >= 0")
        elif type(app.config.tracker) == list and len(app.config.tracker) > 0:
            # config already updated, then we'll consider the first tracker
            if app.config.tracker[0]["type"] == "tracksim":
                cur.execute("UPDATE user SET tracker_in_use = 2 WHERE userid >= 0")
            elif app.config.tracker[0]["type"] == "trucky":
                cur.execute("UPDATE user SET tracker_in_use = 3 WHERE userid >= 0")

    cur.close()
    conn.close()

    print("Upgrade finished")
