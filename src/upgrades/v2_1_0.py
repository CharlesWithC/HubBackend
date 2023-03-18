from db import genconn
from app import config
import traceback

def convertQuotation(s):
    s = str(s)
    return s.replace("\\'","'").replace("'", "\\'")

def process_row(row):
    row = list(row)
    for i in range(len(row)):
        if type(row[i]) == str:
            row[i] = convertQuotation(row[i])
    return row

def run():
    discordid2uid = {}
    userinfo = {}
    userid2uid = {}

    conn = genconn(autocommit = True)
    cur = conn.cursor()

    print(f"Updating user table (reorder, add uid column)...")
    try:
        cur.execute(f"ALTER TABLE user RENAME TO user_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE user")
    cur.execute(f"SELECT * FROM user_old WHERE userid >= 0 ORDER BY userid ASC")
    rows1 = cur.fetchall()
    cur.execute(f"SELECT * FROM user_old WHERE userid = -1 ORDER BY join_timestamp ASC")
    rows2 = cur.fetchall()
    rows = rows1 + rows2
    # userid INT, discordid BIGINT UNSIGNED, name TEXT, avatar TEXT, bio TEXT, email TEXT, truckersmpid BIGINT, steamid BIGINT, roles TEXT, join_timestamp BIGINT, mfa_secret VARCHAR(16)
    cur.execute(f"CREATE TABLE user (uid INT AUTO_INCREMENT PRIMARY KEY, userid INT, name TEXT, email TEXT, avatar TEXT, bio TEXT, roles TEXT, discordid BIGINT UNSIGNED, truckersmpid BIGINT UNSIGNED, steamid BIGINT UNSIGNED, join_timestamp BIGINT, mfa_secret VARCHAR(16))")
    for row in rows:
        row = process_row(row)
        userinfo[row[1]] = row
        if row[7] <= 0:
            row[7] = "NULL"
        if row[6] <= 0:
            row[6] = "NULL"
        try: 
            if row[0] == 0:
                cur.execute(f"INSERT INTO user(uid, userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, join_timestamp, mfa_secret) VALUES (0, {row[0]}, '{row[2]}', '{row[5]}', '{row[3]}', '{row[4]}', '{row[8]}', {row[1]}, {row[7]}, {row[6]}, {row[9]}, '{row[10]}')")
                cur.execute(f"ALTER TABLE user AUTO_INCREMENT = 0;")
            else:
                cur.execute(f"INSERT INTO user(userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, join_timestamp, mfa_secret) VALUES ({row[0]}, '{row[2]}', '{row[5]}', '{row[3]}', '{row[4]}', '{row[8]}', {row[1]}, {row[7]}, {row[6]}, {row[9]}, '{row[10]}')")
        except:
            traceback.print_exc()
        cur.execute(f"SELECT LAST_INSERT_ID();")
        t = cur.fetchone()
        uid = t[0]
        discordid2uid[row[1]] = uid
        if row[0] >= 0:
            userid2uid[row[0]] = uid
    print(f"Created {len(list(discordid2uid.keys()))} discordid -> uid links.")
    
    print(f"Updating user_password table (discordid -> uid)...")
    try:
        cur.execute(f"ALTER TABLE user_password RENAME TO user_password_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE user_password")
    cur.execute(f"SELECT * FROM user_password_old")
    rows = cur.fetchall()
    cur.execute(f"CREATE TABLE user_password (uid INT, email TEXT, password TEXT)")
    for row in rows:
        row = process_row(row)
        if not row[0] in discordid2uid.keys():
            # print(f"[WARN] Skipped {row[0]}: User does not exist.")
            continue
        try:
            cur.execute(f"INSERT INTO user_password VALUES ({discordid2uid[row[0]]}, '{row[1]}', '{row[2]}')")
        except:
            traceback.print_exc()
    
    print(f"Updating user_activity table (discordid -> uid)...")
    try:
        cur.execute(f"ALTER TABLE user_activity RENAME TO user_activity_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE user_activity")
    cur.execute(f"SELECT * FROM user_activity_old")
    rows = cur.fetchall()
    cur.execute(f"CREATE TABLE user_activity (uid INT, activity TEXT, timestamp BIGINT)")
    for row in rows:
        row = process_row(row)
        if not row[0] in discordid2uid.keys():
            # print(f"[WARN] Skipped {row[0]}: User does not exist.")
            continue
        try:
            cur.execute(f"INSERT INTO user_activity VALUES ({discordid2uid[row[0]]}, '{row[1]}', {row[2]})")
        except:
            traceback.print_exc()
    
    print(f"Updating user_notification table (discordid -> uid)...")
    try:
        cur.execute(f"ALTER TABLE user_notification RENAME TO user_notification_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE user_notification")
    cur.execute(f"SELECT * FROM user_notification_old")
    rows = cur.fetchall()
    cur.execute(f"CREATE TABLE user_notification (notificationid INT AUTO_INCREMENT PRIMARY KEY, uid INT, content TEXT, timestamp BIGINT, status INT)")
    for row in rows:
        row = process_row(row)
        if not row[1] in discordid2uid.keys():
            # print(f"[WARN] Skipped {row[1]}: User does not exist.")
            continue
        try:
            cur.execute(f"INSERT INTO user_notification VALUES ({row[0]}, {discordid2uid[row[1]]}, '{row[2]}', {row[3]}, {row[4]})")
        except:
            traceback.print_exc()
    
    print(f"Updating banned table (discordid -> uid)...")
    try:
        cur.execute(f"ALTER TABLE banned RENAME TO banned_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE banned")
    cur.execute(f"SELECT * FROM banned_old")
    rows = cur.fetchall()
    cur.execute(f"CREATE TABLE banned (uid INT, email TEXT, discordid BIGINT UNSIGNED, steamid BIGINT UNSIGNED, truckersmpid BIGINT UNSIGNED, expire_timestamp BIGINT, reason TEXT)")
    for row in rows:
        row = process_row(row)
        if not row[0] in discordid2uid.keys():
            # print(f"[WARN] Skipped {row[0]}: User does not exist.")
            continue
        email = userinfo[row[0]][5]
        steamid = userinfo[row[0]][7]
        truckersmpid = userinfo[row[0]][6]
        try:
            cur.execute(f"INSERT INTO banned VALUES ({discordid2uid[row[0]]}, '{email}', {row[0]}, {steamid}, {truckersmpid}, {row[1]}, '{row[2]}')")
        except:
            traceback.print_exc()
    
    print(f"Updating application table (discordid -> uid)...")
    try:
        cur.execute(f"ALTER TABLE application RENAME TO application_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE application")
    cur.execute(f"SELECT * FROM application_old")
    rows = cur.fetchall()
    cur.execute(f"CREATE TABLE application (applicationid INT AUTO_INCREMENT PRIMARY KEY, application_type INT, uid INT, data TEXT, status INT, submit_timestamp BIGINT, update_staff_userid INT, update_staff_timestamp BIGINT) DATA DIRECTORY = '{config.mysql_ext}'")
    for row in rows:
        row = process_row(row)
        if not row[2] in discordid2uid.keys():
            # print(f"[WARN] Skipped {row[2]}: User does not exist.")
            continue
        try:
            cur.execute(f"INSERT INTO application(applicationid, application_type, uid, data, status, submit_timestamp, update_staff_userid, update_staff_timestamp) VALUES ({row[0]}, {row[1]}, {discordid2uid[row[2]]}, '{row[3]}', {row[4]}, {row[5]}, {row[6]}, {row[5]})")
        except:
            traceback.print_exc()
    
    print(f"Updating session table (discordid -> uid)...")
    try:
        cur.execute(f"ALTER TABLE session RENAME TO session_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE session")
    cur.execute(f"SELECT * FROM session_old")
    rows = cur.fetchall()
    cur.execute(f"CREATE TABLE session (token CHAR(36), uid INT, timestamp BIGINT, ip TEXT, country TEXT, user_agent TEXT, last_used_timestamp BIGINT)")
    for row in rows:
        row = process_row(row)
        if not row[1] in discordid2uid.keys():
            # print(f"[WARN] Skipped {row[1]}: User does not exist.")
            continue
        try:
            cur.execute(f"INSERT INTO session VALUES ('{row[0]}', {discordid2uid[row[1]]}, {row[2]}, '{row[3]}', '{row[4]}', '{row[5]}', {row[6]})")
        except:
            traceback.print_exc()

    print(f"Updating auth_ticket table (discordid -> uid)...")
    try:
        cur.execute(f"ALTER TABLE temp_identity_proof RENAME TO temp_identity_proof_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE auth_ticket")
    cur.execute(f"SELECT * FROM temp_identity_proof_old")
    rows = cur.fetchall()
    try:
        cur.execute(f"CREATE TABLE auth_ticket (token CHAR(36), uid BIGINT UNSIGNED, expire BIGINT)")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            cur.execute(f"DELETE FROM auth_ticket")
    for row in rows:
        row = process_row(row)
        if not row[1] in discordid2uid.keys():
            # print(f"[WARN] Skipped {row[1]}: User does not exist.")
            continue
        try:
            cur.execute(f"INSERT INTO auth_ticket VALUES ('{row[0]}', {discordid2uid[row[1]]}, {row[2]})")
        except:
            traceback.print_exc()

    print(f"Updating application_token table (discordid -> uid)...")
    try:
        cur.execute(f"ALTER TABLE application_token RENAME TO application_token_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE application_token")
    cur.execute(f"SELECT * FROM application_token_old")
    rows = cur.fetchall()
    cur.execute(f"CREATE TABLE application_token (app_name TEXT, token CHAR(36), uid BIGINT UNSIGNED, timestamp BIGINT, last_used_timestamp BIGINT)")
    for row in rows:
        row = process_row(row)
        if not row[2] in discordid2uid.keys():
            # print(f"[WARN] Skipped {row[2]}: User does not exist.")
            continue
        try:
            cur.execute(f"INSERT INTO application_token VALUES ('{row[0]}', '{row[1]}', {discordid2uid[row[2]]}, {row[3]}, {row[4]})")
        except:
            traceback.print_exc()

    print(f"Updating auditlog table (userid -> uid)...")
    try:
        cur.execute(f"ALTER TABLE auditlog RENAME TO auditlog_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE auditlog")
    cur.execute(f"SELECT * FROM auditlog_old")
    rows = cur.fetchall()
    cur.execute(f"CREATE TABLE auditlog (uid INT, operation TEXT, timestamp BIGINT)")
    for row in rows:
        row = process_row(row)
        if not row[0] in userid2uid.keys():
            # print(f"[WARN] Skipped {row[0]}: User does not exist.")
            continue
        try:
            cur.execute(f"INSERT INTO auditlog VALUES ({userid2uid[row[0]]}, '{row[1]}', {row[2]})")
        except:
            traceback.print_exc()
    
    print(f"Updating settings table (discordid -> uid)...")
    try:
        cur.execute(f"ALTER TABLE settings RENAME TO settings_old")
    except Exception as exc:
        if str(exc).find("already exists") != -1:
            print(f"Last upgrade seems to be failed, fixing up...")
            cur.execute(f"DROP TABLE settings")
    cur.execute(f"SELECT * FROM settings_old")
    rows = cur.fetchall()
    cur.execute(f"CREATE TABLE settings (uid BIGINT UNSIGNED, skey TEXT, sval TEXT)")
    for row in rows:
        if row[0] <= 0:
            try:
                cur.execute(f"INSERT INTO settings VALUES (NULL, '{row[1]}', '{row[2]}')")
            except:
                traceback.print_exc()
        else:
            if not row[0] in discordid2uid.keys():
                # print(f"[WARN] Skipped {row[0]}: User does not exist.")
                continue
            try:
                cur.execute(f"INSERT INTO settings VALUES ({discordid2uid[row[0]]}, '{row[1]}', '{row[2]}')")
            except:
                traceback.print_exc()
    
    skey2table = {"nxtnotificationid": "user_notification", "nxtlogid": "dlog", "nxtappid": "application", "nxtannid": "announcement", "nxtchallengeid": "challenge", "nxtdownloadsid": "downloads", "nxteventid": "event"}
    print(f"Updating tables (add AUTO_INCREMENT property)")
    for skey in skey2table.keys():
        table = skey2table[skey]
        if table in ["user", "user_notification"]:
            continue
        idcolumn = table + "id"
        if table == "dlog":
            idcolumn = "logid"
            try:
                cur.execute(f"ALTER IGNORE TABLE {table} MODIFY COLUMN {idcolumn} INT NOT NULL")
                cur.execute(f"ALTER IGNORE TABLE {table} DROP PRIMARY KEY")
            except:
                pass
            cur.execute(f"ALTER IGNORE TABLE {table} MODIFY COLUMN {idcolumn} INT NOT NULL AUTO_INCREMENT")
        else:
            try:
                cur.execute(f"ALTER IGNORE TABLE {table} MODIFY COLUMN {idcolumn} INT NOT NULL")
                cur.execute(f"ALTER IGNORE TABLE {table} DROP PRIMARY KEY")
            except:
                pass
            cur.execute(f"ALTER IGNORE TABLE {table} MODIFY COLUMN {idcolumn} INT NOT NULL AUTO_INCREMENT PRIMARY KEY")

    print(f"Updating settings table (nxtid)...")
    for skey in skey2table.keys():
        cur.execute(f"SELECT sval FROM settings WHERE skey = '{skey}'")
        sval = cur.fetchone()[0]
        cur.execute(f"ALTER TABLE {skey2table[skey]} AUTO_INCREMENT={sval};")
        cur.execute(f"DELETE FROM settings WHERE skey = '{skey}'")
    
    cur.close()
    conn.close()
    
    print(f"Upgrade finished")