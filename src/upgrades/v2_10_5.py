# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This upgrade recompresses zlib-compressed data with zstd
# decompress has been modified to use zstd and fallback to zlib on error
# compress will always use zstd only

from db import genconn
from functions import decompress, compress
from logger import logger


COMPRESSED_TABLE_COLUMNS = [
    ('telemetry.data', 'logid'),
    ('dlog.data', 'logid'),
    ('announcement.content', 'announcementid'),
    ('application.data', 'applicationid'),
    ('challenge.description', 'challengeid'),
    ('challenge.job_requirements', 'challengeid'),
    ('division.message', 'logid'),
    ('downloads.description', 'downloadsid'),
    ('event.description', 'eventid'),
    ('event.link', 'eventid'),
    ('poll.description', 'pollid'),
    ('task.description', 'taskid')]

def run(app):
    conn = genconn(app, autocommit = False)
    cur = conn.cursor()

    logger.info("Changing compress algorithm from zlib to zstd for various tables")
    for table_column in COMPRESSED_TABLE_COLUMNS:
        (table, column) = table_column[0].split('.')
        key = table_column[1]
        try:
            cur.execute("START TRANSACTION")
            cur.execute(f"SELECT {key}, {column} FROM {table}")
            rows = cur.fetchall()
            for row in rows:
                try:
                    data = decompress(row[1])
                    compressed = compress(data)
                    if data == row[1]:
                        logger.warning(f"Skipped TABLE {table_column} ROW {key} = {row[0]} due to original data not compressed")
                        continue
                    cur.execute(f"UPDATE {table} SET {column} = %s WHERE {key} = %s", (compressed, row[0]))
                except:
                    logger.error(f"Failed to recompress {table_column} TABLE ({key} = {row[0]})")
                    import traceback
                    traceback.print_exc()
            cur.execute("COMMIT")
        except:
            cur.execute("ROLLBACK")
            logger.error(f"Failed to recompress {table_column} TABLE")
            import traceback
            traceback.print_exc()

    cur.close()
    conn.close()

    logger.info("Upgrade finished")
