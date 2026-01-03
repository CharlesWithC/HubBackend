# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This upgrade changes all "None" (string) email in database to NULL (NULL)

from db import genconn
from logger import logger


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    logger.info("Updating user TABLE")
    cur.execute("UPDATE user SET email = NULL WHERE email = 'None'")

    cur.close()
    conn.close()

    logger.info("Upgrade finished")
