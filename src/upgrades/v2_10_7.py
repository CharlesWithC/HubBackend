# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This upgrade adds distance column to division table
# and calculates the data for distance attribute

from db import genconn
from logger import logger


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    try:
        cur.execute("SELECT distance FROM division LIMIT 1")

        # if it goes through, then data has been updated
        # mess-up #1: wrong datatype
        # mess-up #2: swapped distance and userid for new requests
        try:
            logger.info("Fixing potentially messed-up data")
            cur.execute("ALTER TABLE division MODIFY distance DOUBLE")
            correct_data = {}
            cur.execute("SELECT logid, userid, distance, timestamp FROM dlog")
            t = cur.fetchall()
            for tt in t:
                correct_data[tt[0]] = [tt[1], tt[2], tt[3]]

            for tt in t:
                cur.execute(f"UPDATE division SET distance = {tt[2]} WHERE logid = {tt[0]}")
                if tt[3] >= 1740718800:
                    cur.execute(f"UPDATE division SET userid = {tt[1]} WHERE logid = {tt[0]}")
        except:
            pass
    except:
        logger.info("Updating division TABLE")
        cur.execute("ALTER TABLE division ADD distance DOUBLE AFTER userid")
        cur.execute("SELECT logid, distance FROM dlog")
        t = cur.fetchall()
        for tt in t:
            cur.execute(f"UPDATE division SET distance = {tt[1]} WHERE logid = {tt[0]}")

    cur.close()
    conn.close()

    logger.info("Upgrade finished")
