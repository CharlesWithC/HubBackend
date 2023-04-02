from app import app
from db import genconn
from functions.userinfo import getAvatarSrc


def run():
    conn = genconn(autocommit = True)
    cur = conn.cursor()

    print("Getting %_old TABLES...")
    cur.execute(f"SELECT CONCAT('DROP TABLE ', TABLE_NAME, ';') AS 'SQL' FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{app.config.abbr}_drivershub' AND TABLE_NAME LIKE '%_old';")
    t = cur.fetchall()
    if len(t) > 0:
        print("Dropping %_old TABLES...")
        for tt in t:
            print(tt[0])
            cur.execute(tt[0])
    else:
        print("No %_old TABLE found")
    
    print("Deleting abandoned tables...")
    TABLES = ["appsession", "dlogcache"]
    for TABLE in TABLES:
        try:
            cur.execute(f"DROP TABLE {TABLE};")
        except:
            pass

    cur.close()
    conn.close()
    
    print(f"Upgrade finished")