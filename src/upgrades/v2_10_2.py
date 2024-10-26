# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This upgrade builds 'dlog_meta' table from 'dlog.data'

import json

from db import genconn
from functions import convertQuotation, decompress
from logger import logger


def run(app):
    conn = genconn(app, autocommit = True)
    cur = conn.cursor()

    try:
        logger.info("Seeding dlog_meta TABLE")
        cur.execute("DELETE FROM dlog_meta")
        cur.execute("SELECT logid, data FROM dlog")
        t = cur.fetchall()
        for tt in t:
            (logid, data) = tt
            manual = (logid < 0)

            if manual:
                try:
                    data = json.loads(data)
                except:
                    # old manual distance does not have json data, rather, it's an empty string
                    data = {"staff_userid": -1, "note": ""}

                meta_note = f"{data['staff_userid']}, {data['note']}"
                cur.execute(f"INSERT INTO dlog_meta (logid, note) VALUES ({logid}, '{convertQuotation(meta_note)}')")

            else:
                try:
                    data = json.loads(decompress(data))
                except:
                    data = {}

                source_city = "N/A"
                source_company = "N/A"
                destination_city = "N/A"
                destination_company = "N/A"
                if "data" in data.keys() and data["data"]["object"]["source_city"] is not None:
                    source_city = data["data"]["object"]["source_city"]["name"]
                if "data" in data.keys() and data["data"]["object"]["source_company"] is not None:
                    source_company = data["data"]["object"]["source_company"]["name"]
                if "data" in data.keys() and data["data"]["object"]["destination_city"] is not None:
                    destination_city = data["data"]["object"]["destination_city"]["name"]
                if "data" in data.keys() and data["data"]["object"]["destination_company"] is not None:
                    destination_company = data["data"]["object"]["destination_company"]["name"]
                cargo_name = "N/A"
                cargo_mass = 0
                if "data" in data.keys() and data["data"]["object"]["cargo"] is not None:
                    cargo_name = data["data"]["object"]["cargo"]["name"]
                    cargo_mass = data["data"]["object"]["cargo"]["mass"]

                cur.execute(f"INSERT INTO dlog_meta (logid, source_city, source_company, destination_city, destination_company, cargo_name, cargo_mass) VALUES ({logid}, '{convertQuotation(source_city)}', '{convertQuotation(source_company)}', '{convertQuotation(destination_city)}', '{convertQuotation(destination_company)}', '{convertQuotation(cargo_name)}', {cargo_mass})")
    except:
        logger.error("Failed to seed dlog_meta TABLE")
        import traceback
        traceback.print_exc()

    cur.close()
    conn.close()

    logger.info("Upgrade finished")
