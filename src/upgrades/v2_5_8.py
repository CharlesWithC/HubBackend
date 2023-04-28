# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from db import genconn


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()
    
    print("Renaming 'source' COLUMN to `callback_url` in 'discord_access_token' TABLE")
    try:
        cur.execute("ALTER TABLE discord_access_token RENAME COLUMN source TO callback_url")
        cur.execute("DELETE FROM discord_access_token") # previous source cannot be used as callback_url
    except:
        pass

    cur.close()
    conn.close()
    
    print("Upgrade finished")