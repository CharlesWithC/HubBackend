from db import genconn


def run(app):
    conn = genconn(autocommit = True)
    cur = conn.cursor()

    print(f"Moving application to DATA DIRECTORY...")
    cur.execute(f"ALTER TABLE application DATA DIRECTORY = '{app.config.mysql_ext}'")

    print("Fixing nxtuserid in settings...")
    cur.execute(f"SELECT MAX(userid) FROM user")
    nxtuserid = cur.fetchone()[0] + 1
    if nxtuserid is None:
        nxtuserid = 1
    print(f"Max userid in user table is {(nxtuserid-1)}.")
    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtuserid'")
    t = cur.fetchall()
    if len(t) == 0:
        print(f"nxtuserid not in settings, added.")
        cur.execute(F"INSERT INTO settings VALUES (NULL, 'nxtuserid', '{nxtuserid}')")
    else:
        suserid = int(t[0][0])
        print(f"nxtuserid in settings is {suserid}")
        if suserid < nxtuserid:
            print(f"updated nxtuserid in settings to {nxtuserid}")
            cur.execute(f"UPDATE settings SET sval = '{nxtuserid}' WHERE skey = 'nxtuserid'")
    conn.commit()
    
    cur.close()
    conn.close()
    
    print(f"Upgrade finished")