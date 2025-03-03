# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from db import genconn
from logger import logger


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    logger.info("Getting %_old TABLES...")
    cur.execute(f"SELECT CONCAT('DROP TABLE ', TABLE_NAME, ';') AS 'SQL' FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{app.config.abbr}_drivershub' AND TABLE_NAME LIKE '%_old';")
    t = cur.fetchall()
    if len(t) > 0:
        logger.info("Dropping %_old TABLES...")
        for tt in t:
            logger.info(tt[0])
            cur.execute(tt[0])
    else:
        logger.info("No %_old TABLE found")

    logger.info("Deleting abandoned tables...")
    TABLES = ["appsession", "dlogcache"]
    for TABLE in TABLES:
        try:
            cur.execute(f"DROP TABLE {TABLE};")
        except:
            pass

    cur.close()
    conn.close()

    logger.info("Upgrade finished")
