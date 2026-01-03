# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from db import genconn
from functions.userinfo import getAvatarSrc
from logger import logger


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    logger.info("Updating ratelimit table...")
    try:
        cur.execute("ALTER TABLE ratelimit RENAME COLUMN ip TO identifier")
    except:
        logger.info("Failed, potentially due to previous incomplete upgrade")

    logger.info("Updating user table (avatar column)...")
    cur.execute("SELECT uid, discordid, avatar FROM user")
    t = cur.fetchall()
    for tt in t:
        uid = tt[0]
        discordid = tt[1]
        avatar = tt[2]
        if "://" not in avatar:
            avatar = getAvatarSrc(discordid, avatar)
            cur.execute(f"UPDATE user SET avatar = '{avatar}' WHERE uid = {uid}")

    cur.close()
    conn.close()

    logger.info("Upgrade finished")
