# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from db import genconn


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    try:
        cur.execute("SELECT is_pinned FROM announcement LIMIT 1")
    except:
        print("Updating announcement TABLE")
        cur.execute("ALTER TABLE announcement ADD orderid INT")
        cur.execute("ALTER TABLE announcement ADD is_pinned INT")
        cur.execute("UPDATE announcement SET orderid = 0, is_pinned = 0")

    try:
        cur.execute("SELECT is_pinned FROM downloads LIMIT 1")
    except:
        print("Updating downloads TABLE")
        cur.execute("ALTER TABLE downloads ADD is_pinned INT AFTER orderid")
        cur.execute("ALTER TABLE downloads ADD timestamp INT AFTER is_pinned")
        cur.execute("UPDATE downloads SET timestamp = 0, is_pinned = 0")

    cur.close()
    conn.close()

    print("Upgrade finished")
