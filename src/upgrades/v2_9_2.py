# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This upgrade adds note and staff_userid column in bouns_point

from db import genconn
from logger import logger


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    try:
        cur.execute("SELECT staff_userid FROM bonus_point LIMIT 1")
    except:
        logger.info("Updating bonus_point TABLE")
        cur.execute("ALTER TABLE bonus_point ADD note VARCHAR(256) AFTER point")
        cur.execute("ALTER TABLE bonus_point ADD staff_userid INT AFTER note")
        cur.execute("UPDATE bonus_point SET note = '' WHERE note IS NULL")

    cur.close()
    conn.close()

    logger.info("Upgrade finished")
