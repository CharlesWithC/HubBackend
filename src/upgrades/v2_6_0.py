# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from db import genconn


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    print("Converting INT to BIGINT 'economy_*' TABLE")
    try:
        cur.execute("ALTER TABLE economy_truck MODIFY COLUMN price BIGINT UNSIGNED")
        cur.execute("ALTER TABLE economy_garage MODIFY COLUMN price BIGINT UNSIGNED")
        cur.execute("ALTER TABLE economy_merch MODIFY COLUMN buy_price BIGINT UNSIGNED")
        cur.execute("ALTER TABLE economy_merch MODIFY COLUMN sell_price BIGINT UNSIGNED")
        cur.execute("ALTER TABLE economy_transaction MODIFY COLUMN from_new_balance BIGINT")
        cur.execute("ALTER TABLE economy_transaction MODIFY COLUMN to_new_balance BIGINT")
    except:
        pass

    cur.close()
    conn.close()

    print("Upgrade finished")
