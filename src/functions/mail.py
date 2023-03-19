# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import socks
from aiosmtplib import SMTP

from app import config, tconfig


def emailConfigured():
    return config.smtp_host != "" and config.smtp_port != "" and config.smtp_email != "" and config.smtp_passwd != ""

async def sendEmail(name, email, category, link):
    if not category in tconfig["email_template"].keys():
        raise ValueError("Invalid Category")

    if not emailConfigured():
        return False

    message = MIMEMultipart('alternative')
    message['From'] = tconfig["email_template"][category]["from_email"]
    message['To'] = f"{name} <{email}>"
    message['Subject'] = tconfig["email_template"][category]["subject"]

    plain_text = MIMEText(tconfig["email_template"][category]["plain"].replace("{link}", link), 'plain')
    message.attach(plain_text)
    html_text = MIMEText(tconfig["email_template"][category]["html"].replace("{link}", link), 'html')
    message.attach(html_text)
    
    s = socks.socksocket()

    proxy_url = os.environ.get('SOCKS_PROXY')
    if proxy_url:
        r = re.match(r'socks(.*)://([^:/]+):(\d+)', proxy_url)
        if r:
            socksv = socks.SOCKS5
            if r.group(1) == "4":
                socksv = socks.SOCKS4
            proxy_host = r.group(2)
            proxy_port = int(r.group(3))
            s.set_proxy(socksv, proxy_host, proxy_port)

    s.connect((config.smtp_host, int(config.smtp_port)))

    try:
        async with SMTP(sock=s, local_hostname="drivershub", source_address=("drivershub.charlws.com", 0), hostname=None, port=None, socket_path=None, timeout = 10) as session:
            await session.login(config.smtp_email, config.smtp_passwd)
            await session.send_message(message)
            await session.quit()
        s.close()
        return True
    except:
        s.close()
        return False