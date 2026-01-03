# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from db import genconn
from logger import logger


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    logger.info("Moving application to DATA DIRECTORY...")
    cur.execute(f"ALTER TABLE application DATA DIRECTORY = '{app.config.db_data_directory}'")

    logger.info("Fixing nxtuserid in settings...")
    cur.execute("SELECT MAX(userid) FROM user")
    nxtuserid = cur.fetchone()[0] + 1
    if nxtuserid is None:
        nxtuserid = 1
    logger.info(f"Max userid in user table is {(nxtuserid-1)}.")
    cur.execute("SELECT sval FROM settings WHERE skey = 'nxtuserid'")
    t = cur.fetchall()
    if len(t) == 0:
        logger.info("nxtuserid not in settings, added.")
        cur.execute(F"INSERT INTO settings VALUES (NULL, 'nxtuserid', '{nxtuserid}')")
    else:
        suserid = int(t[0][0])
        logger.info(f"nxtuserid in settings is {suserid}")
        if suserid < nxtuserid:
            logger.info(f"updated nxtuserid in settings to {nxtuserid}")
            cur.execute(f"UPDATE settings SET sval = '{nxtuserid}' WHERE skey = 'nxtuserid'")
    conn.commit()

    cur.close()
    conn.close()

    logger.info("Upgrade finished")
