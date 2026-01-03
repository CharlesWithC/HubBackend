# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This upgrade adds category column in auditlog

from db import genconn
from logger import logger


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    try:
        cur.execute("SELECT category FROM auditlog LIMIT 1")
    except:
        logger.info("Updating auditlog TABLE")
        cur.execute("ALTER TABLE auditlog ADD category VARCHAR(32) AFTER uid")
        cur.execute("UPDATE auditlog SET category = 'legacy' WHERE category IS NULL")

    cur.close()
    conn.close()

    logger.info("Upgrade finished")
