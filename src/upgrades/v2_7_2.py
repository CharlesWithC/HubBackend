# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from db import genconn


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    try:
        cur.execute("SELECT is_pinned FROM event LIMIT 1")
    except:
        print("Reordering event TABLE COLUMN")
        cur.execute("""CREATE TABLE IF NOT EXISTS new_event (
                        eventid INT AUTO_INCREMENT PRIMARY KEY,
                        userid INT,
                        title TEXT,
                        description TEXT,
                        link TEXT,
                        departure TEXT,
                        destination TEXT,
                        distance TEXT,
                        meetup_timestamp BIGINT,
                        departure_timestamp BIGINT,
                        is_private INT,
                        vote TEXT,
                        attendee TEXT,
                        points INT
                    )""")
        cur.execute("SELECT COUNT(*) FROM event")
        t = cur.fetchall()
        if len(t) == 0 or t[0][0] == 0:
            cur.execute("DROP TABLE event")
            cur.execute("""ALTER TABLE new_event RENAME TO event""")
        else:
            cur.execute("""INSERT INTO new_event (
                            eventid,
                            userid,
                            title,
                            description,
                            link,
                            departure,
                            destination,
                            distance,
                            meetup_timestamp,
                            departure_timestamp,
                            is_private,
                            vote,
                            attendee,
                            points
                        )
                        SELECT eventid,
                            userid,
                            title,
                            description,
                            link,
                            departure,
                            destination,
                            distance,
                            meetup_timestamp,
                            departure_timestamp,
                            is_private,
                            vote,
                            attendee,
                            points FROM event""")
            cur.execute("""SELECT MAX(eventid) INTO @max_eventid FROM event""")
            cur.execute("""SET @sql = CONCAT('ALTER TABLE new_event AUTO_INCREMENT = ', @max_eventid + 1)""")
            cur.execute("""PREPARE stmt FROM @sql""")
            cur.execute("""EXECUTE stmt""")
            cur.execute("""DEALLOCATE PREPARE stmt""")
            cur.execute("""DROP TABLE event""")
            cur.execute("""ALTER TABLE new_event RENAME TO event""")

        print("Updating event TABLE")
        cur.execute("ALTER TABLE event ADD orderid INT AFTER is_private")
        cur.execute("ALTER TABLE event ADD is_pinned INT AFTER orderid")
        cur.execute("UPDATE event SET orderid = 0, is_pinned = 0")

    cur.close()
    conn.close()

    print("Upgrade finished")
