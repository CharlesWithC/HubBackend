from db import genconn
from functions.userinfo import getAvatarSrc


def run(app):
    conn = genconn(autocommit = True)
    cur = conn.cursor()

    print("Updating ratelimit table...")
    try:
        cur.execute(f"ALTER TABLE ratelimit RENAME COLUMN ip TO identifier")
    except:
        print("Failed, potentially due to previous incomplete upgrade")

    print("Updating user table (avatar column)...")
    cur.execute(f"SELECT uid, discordid, avatar FROM user")
    t = cur.fetchall()
    for tt in t:
        uid = tt[0]
        discordid = tt[1]
        avatar = tt[2]
        if not "://" in avatar:
            avatar = getAvatarSrc(discordid, avatar)
            cur.execute(f"UPDATE user SET avatar = '{avatar}' WHERE uid = {uid}")
    
    cur.close()
    conn.close()
    
    print(f"Upgrade finished")