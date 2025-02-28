# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This upgrade adds distance column to division table
# and calculates the data for distance attribute

from db import genconn


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    try:
        cur.execute("SELECT distance FROM division LIMIT 1")
    except:
        print("Updating division TABLE")
        cur.execute("ALTER TABLE division ADD distance INT AFTER userid")
        cur.execute("SELECT logid, distance FROM dlog")
        t = cur.fetchall()
        for tt in t:
            cur.execute(f"UPDATE division SET distance = {tt[1]} WHERE logid = {tt[0]}")

    cur.close()
    conn.close()

    print("Upgrade finished")
