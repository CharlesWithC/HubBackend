# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This upgrade adds category column in auditlog

from db import genconn


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    try:
        cur.execute("SELECT category FROM auditlog LIMIT 1")
    except:
        print("Updating auditlog TABLE")
        cur.execute("ALTER TABLE auditlog ADD category VARCHAR(32) AFTER uid")
        cur.execute("UPDATE auditlog SET category = 'legacy' WHERE category IS NULL")

    cur.close()
    conn.close()

    print("Upgrade finished")
