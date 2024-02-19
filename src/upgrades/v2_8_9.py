# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This upgrade changes all "None" (string) email in database to NULL (NULL)

from db import genconn


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    print("Updating user TABLE")
    cur.execute("UPDATE user SET email = NULL WHERE email = 'None'")

    cur.close()
    conn.close()

    print("Upgrade finished")
