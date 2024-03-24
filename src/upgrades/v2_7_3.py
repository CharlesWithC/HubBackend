# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from db import genconn


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    try:
        cur.execute("SELECT timestamp FROM challenge LIMIT 1")
    except:
        print("Updating challenge TABLE")
        cur.execute("ALTER TABLE challenge ADD timestamp BIGINT AFTER job_requirements")
        cur.execute("UPDATE challenge SET timestamp = 0")

    try:
        cur.execute("SELECT timestamp FROM event LIMIT 1")
    except:
        print("Updating event TABLE")
        cur.execute("ALTER TABLE event ADD timestamp BIGINT AFTER is_pinned")
        cur.execute("UPDATE event SET timestamp = 0")

    cur.close()
    conn.close()

    print("Upgrade finished")
