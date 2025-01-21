# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import socks
from aiosmtplib import SMTP


def emailConfigured(app):
    return app.config.smtp_host != "" and app.config.smtp_port != "" and app.config.smtp_email != "" and app.config.smtp_password != ""

async def sendEmail(app, name, email, category, link):
    if category not in app.config.__dict__["email_template"].__dict__.keys():
        raise ValueError("Invalid Category")

    if not emailConfigured(app):
        return False

    message = MIMEMultipart('mixed')
    message['From'] = app.config.__dict__["email_template"].__dict__[category].__dict__["from_email"]
    message['To'] = f"{name} <{email}>"
    message['Subject'] = app.config.__dict__["email_template"].__dict__[category].__dict__["subject"]

    msgAlternative = MIMEMultipart('alternative')
    message.attach(msgAlternative)

    plain_text = MIMEText(
        app.config.__dict__["email_template"].__dict__[category].__dict__["plain"].replace("{link}", link),
        'plain', 'utf-8'
    )
    html_text = MIMEText(
        app.config.__dict__["email_template"].__dict__[category].__dict__["html"].replace("{link}", link),
        'html', 'utf-8'
    )

    # first attach plain then html
    msgAlternative.attach(plain_text)
    msgAlternative.attach(html_text)

    try:
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

        s.connect((app.config.smtp_host, int(app.config.smtp_port)))

        async with SMTP(sock=s, local_hostname="drivershub", source_address=("drivershub.charlws.com", 0), hostname=None, port=None, socket_path=None, timeout=10) as session:
            await session.login(app.config.smtp_email, app.config.smtp_password)
            await session.send_message(message)
            await session.quit()
        s.close()
        return True
    except:
        s.close()
        return False
