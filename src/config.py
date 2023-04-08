# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import copy


def isfloat(t):
    try:
        float(t)
        return True
    except:
        return False

config_keys_order = ['abbr', 'name', 'language', 'distance_unit', 'privacy', 'hex_color', 'logo_url', 'openapi', 'frontend_urls', 'apidomain', 'domain', 'server_host', 'server_port', 'server_workers', 'whitelist_ips', 'webhook_error', 'database', 'mysql_host', 'mysql_user', 'mysql_passwd', 'mysql_db', 'mysql_ext', 'mysql_pool_size', 'hcaptcha_secret', 'plugins', 'external_plugins', 'guild_id', 'must_join_guild', 'use_server_nickname', 'allow_custom_profile', 'avatar_domain_whitelist', 'required_connections', 'register_methods', 'tracker', 'tracker_company_id', 'tracker_api_token', 'tracker_webhook_secret', 'allowed_tracker_ips', 'delivery_rules', 'delivery_log_channel_id', 'delivery_post_gifs', 'discord_client_id', 'discord_client_secret', 'discord_bot_token', 'steam_api_key', 'smtp_host', 'smtp_port', 'smtp_email', 'smtp_passwd', 'email_template', 'member_accept', 'member_welcome', 'member_leave', 'rank_up', 'ranks', 'application_types', 'webhook_division', 'webhook_division_message', 'divisions', 'economy', 'perms', 'roles', 'webhook_audit']

config_whitelist = ['name', 'language', 'distance_unit', 'privacy', 'hex_color', 'logo_url', 'guild_id', 'must_join_guild', 'use_server_nickname', 'allow_custom_profile', 'avatar_domain_whitelist', 'required_connections', 'register_methods', 'tracker', 'tracker_company_id', 'tracker_api_token', 'tracker_webhook_secret', 'allowed_tracker_ips', 'delivery_rules','delivery_log_channel_id', 'delivery_post_gifs', 'discord_client_id', 'discord_client_secret', 'discord_bot_token', 'steam_api_key', 'smtp_host', 'smtp_port', 'smtp_email', 'smtp_passwd', 'email_template', 'member_accept', 'member_welcome', 'member_leave', 'rank_up', 'ranks', 'application_types', 'webhook_division', 'webhook_division_message', 'divisions', 'economy', 'perms', 'roles', 'webhook_audit']

config_plugins = {"application": ["application_types"],
    "division": ["webhook_division", "webhook_division_message", "divisions"],
    "economy": ["economy"]}

config_protected = ["tracker_api_token", "tracker_webhook_secret", "discord_client_secret", "discord_bot_token", "steam_api_key", "smtp_passwd"]

default_config = {
    "abbr": "",
    "name": "",
    "language": "en",
    "distance_unit": "metric",
    "privacy": False,
    "hex_color": "FFFFFF",
    "logo_url": "https://{domain}/images/logo.png",

    "openapi": "./openapi.json",
    "frontend_urls": {
        "steam_callback": "https://{domain}/connectSteam",
        "discord_callback": "https://{domain}/connectDiscord",
        "auth_message": "https://{domain}/auth?message={message}",
        "auth_token": "https://{domain}/auth?token={token}",
        "auth_mfa": "https://{domain}/auth?token={token}&mfa=true",
        "member": "https://{domain}/member?userid={userid}",
        "delivery": "https://{domain}/delivery?logid={logid}",
        "email_confirm": "https://{domain}/emailConfirm?secret={secret}"
    },

    "apidomain": "drivershub.charlws.com",
    "domain": "",
    "server_host": "127.0.0.1",
    "server_port": 7777,
    "server_workers": 1,
    "whitelist_ips": [],
    "webhook_error": "",

    "database": "mysql",
    "mysql_host": "localhost",
    "mysql_user": "",
    "mysql_passwd": "",
    "mysql_db": "_drivershub",
    "mysql_ext": "/var/lib/mysqlext/",
    "mysql_pool_size": 10,
    "hcaptcha_secret": "",

    "plugins": [],
    "external_plugins": [],

    "guild_id": "",
    "must_join_guild": True,
    "use_server_nickname": True,
    "allow_custom_profile": True,
    "avatar_domain_whitelist": ["charlws.com", "cdn.discordapp.com", "steamstatic.com"],
    "required_connections": ["discord", "email", "truckersmp"],
    "register_methods": ["email", "discord", "steam"],

    "tracker": "tracksim",
    "tracker_company_id": "",
    "tracker_api_token": "",
    "tracker_webhook_secret": "",
    "allowed_tracker_ips": ["109.106.1.243"],
    "delivery_rules": {
        "max_speed": 180,
        "max_profit": 1000000,
        "action": "block"
    },
    "delivery_log_channel_id": "",
    "delivery_post_gifs": ["https://c.tenor.com/fjTTED8MZxIAAAAC/truck.gif",
        "https://c.tenor.com/QhMgCV8uMvIAAAAC/airtime-weeee.gif",
        "https://c.tenor.com/VYt4iLQJWhcAAAAd/kid-spin.gif",
        "https://c.tenor.com/_aICF_XLbR4AAAAC/ck8car-driving.gif",
        "https://c.tenor.com/jEW-3JELMG4AAAAM/skidding-white-pick-up.gif",
        "https://c.tenor.com/JGw-jxHDAGoAAAAC/truck-lol.gif",
        "https://c.tenor.com/2B9tkbj7CVEAAAAM/explode-truck.gif",
        "https://c.tenor.com/Tl6l934qO70AAAAC/driving-truck.gif",
        "https://c.tenor.com/1SPfoAWWejEAAAAC/chevy-truck.gif",
        "https://c.tenor.com/MfGOJIgU22UAAAAC/ford-f100-truck.gif"],

    "discord_client_id": "",
    "discord_client_secret": "",
    "discord_bot_token": "",
    "steam_api_key": "",
    
    "smtp_host": "",
    "smtp_port": "",
    "smtp_email": "",
    "smtp_passwd": "",
    "email_template": {
        "register": {
            "subject": "Register Acccount",
            "from_email": "VTC <email>",
            "html": "You are registering an account in Drivers Hub. Please click the link below to verify your email.<br>{link}",
            "plain": "You are registering an account in Drivers Hub. Please click the link below to verify your email.\n{link}"
        },
        "update_email": {
            "subject": "Update Email",
            "from_email": "VTC <email>",
            "html": "You are updating your email in Drivers Hub. Please click the link below to verify your email.<br>{link}",
            "plain": "You are updating your email in Drivers Hub. Please click the link below to verify your email.\n{link}"
        },
        "reset_password": {
            "subject": "Reset Password",
            "from_email": "VTC <email>",
            "html": "You are resetting your password in Drivers Hub. Please click the link below to continue.<br>{link}",
            "plain": "You are resetting your password in Drivers Hub. Please click the link below to continue.\n{link}"
        }
    },

    "member_accept": {
        "webhook_url": "",
        "channel_id": "",
        "content": "{mention}",
        "embed": {
            "title": "",
            "description": "{name} has joined **VTC**.",
            "image_url": "",
            "footer": {
                "text": "",
                "icon_url": ""
            },
            "timestamp": True
        }
    },

    "member_welcome": {
        "webhook_url": "",
        "channel_id": "",
        "content": "{mention}",
        "embed": {
            "title": "",
            "description": "Welcome {name}.",
            "image_url": "https://{domain}/images/bg.jpg",
            "footer": {
                "text": "You are our #{userid} driver",
                "icon_url": ""
            },
            "timestamp": True
        },
        "role_change": []
    },
    
    "member_leave": {
        "webhook_url": "",
        "channel_id": "",
        "content": "{mention}",
        "embed": {
            "title": "",
            "description": "Welcome {name}.",
            "image_url": "https://{domain}/images/bg.jpg",
            "footer": {
                "text": "You are our #{userid} driver",
                "icon_url": ""
            },
            "timestamp": True
        },
        "role_change": []
    },

    "rank_up": {
        "webhook_url": "",
        "channel_id": "",
        "content": "{mention}",
        "embed": {
            "title": "",
            "description": "GG {mention}! You have ranked up to {rank}!",
            "image_url": "",
            "footer": {
                "text": "",
                "icon_url": ""
            },
            "timestamp": True
        }
    },
    "ranks": [
        {"points": 0, "name": "New Driver", "color": "#CCCCCC", "discord_role_id": ""}
    ],

    "application_types": [
        {"id": 1, "name": "Driver", "discord_role_id": "", "staff_role_id": [20], "message": "", "webhook": "", "note": "driver"},
        {"id": 2, "name": "Staff", "discord_role_id": "", "staff_role_id": [20], "message": "", "webhook": "", "note": ""},
        {"id": 3, "name": "LOA", "discord_role_id": "", "staff_role_id": [20], "message": "", "webhook": "", "note": ""},
        {"id": 4, "name": "Division", "discord_role_id": "", "staff_role_id": [40], "message": "", "webhook": "", "note": ""}
    ],

    "webhook_division": "",
    "webhook_division_message": "",
    "divisions": [],
    
    "economy": {
        "trucks": [{"id": "daf.xf", "brand": "DAF", "model": "XF 105", "price": 160000}, {"id": "iveco.as2", "brand": "Iveco", "model": "Stralis", "price": 160000}, {"id": "iveco.h_u01", "brand": "Iveco", "model": "Stralis Hi-Way", "price": 180000}, {"id": "man.tgx", "brand": "MAN", "model": "TGX", "price": 150000}, {"id": "man.tgx_euro6", "brand": "MAN", "model": "TGX Euro 6", "price": 180000}, {"id": "actros.towing", "brand": "Mercedes", "model": "New Actros", "price": 205000}, {"id": "renault.magnum", "brand": "Renault", "model": "Magnum", "price": 165000}, {"id": "renault.premium", "brand": "Renault", "model": "Premium", "price": 160000}, {"id": "renault.t", "brand": "Renault", "model": "T", "price": 190000}, {"id": "scania.r_2016", "brand": "Scania", "model": "R", "price": 230000}, {"id": "scania_r", "brand": "Scania", "model": "R2009", "price": 200000}, {"id": "scania.s_2016", "brand": "Scania", "model": "S", "price": 225000}, {"id": "scania.streamline", "brand": "Scania", "model": "Streamline", "price": 220000}, {"id": "volvo.fh3", "brand": "Volvo", "model": "FH16 2009", "price": 195000}, {"id": "volvo.fh16_2012", "brand": "Volvo", "model": "FH16 2012", "price": 210000}, {"id": "freightliner.cascadia2019", "brand": "Freightliner", "model": "Cascadia", "price": 158000}, {"id": "intnational.9900i", "brand": "International", "model": "9900i", "price": 230000}, {"id": "intnational.lonestar", "brand": "International", "model": "Lonestar", "price": 206000}, {"id": "intnational.lt", "brand": "International", "model": "LT", "price": 170000}, {"id": "kenworth.t680", "brand": "Kenworth", "model": "T680", "price": 160000}, {"id": "kenworth.wp", "brand": "Kenworth", "model": "W900", "price": 154000}, {"id": "mack.anthem", "brand": "Mack", "model": "Anthem", "price": 180000}, {"id": "peterbilt.389", "brand": "Peterbilt", "model": "389", "price": 170000}, {"id": "peterbilt.579", "brand": "Peterbilt", "model": "579", "price": 164000}, {"id": "volvo.vnl", "brand": "Volvo", "model": "VNL", "price": 170000}, {"id": "ws", "brand": "Western Star", "model": "5700XE", "price": 210000}, {"id": "westernstar.57x", "brand": "Western Star", "model": "57X", "price": 180000}],
        "garages": [{"id": "spain.acoruna", "name": "A Coruña, Spain", "x": -83140.91, "z": 25857.3438, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "denmark.aalborg", "name": "Aalborg, Denmark", "x": 480.1328, "z": -36290.2227, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.aberdeen", "name": "Aberdeen, United Kingdom", "x": -39596.793, "z": -56040.47, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.ajaccio", "name": "Ajaccio, France", "x": -10531.5977, "z": 47850.7656, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.albacete", "name": "Albacete, Spain", "x": -58355.48, "z": 58394.95, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.algeciras", "name": "Algeciras, Spain", "x": -80942.375, "z": 69036.42, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.almeria", "name": "Almería, Spain", "x": -63728.0039, "z": 69091.0, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "netherlands.amsterdam", "name": "Amsterdam, Netherlands", "x": -19062.1328, "z": -12231.3359, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.ancona", "name": "Ancona, Italy", "x": 9981.145, "z": 39438.16, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "slovakia.banskabystrica", "name": "Banská Bystrica, Slovakia", "x": 32257.457, "z": 10360.3516, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.barcelona", "name": "Barcelona, Spain", "x": -40360.1172, "z": 47101.86, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.bari", "name": "Bari, Italy", "x": 23031.04, "z": 53831.2734, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.bastia", "name": "Bastia, France", "x": -7539.672, "z": 43566.22, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "norway.bergen", "name": "Bergen, Norway", "x": -10571.707, "z": -56397.7656, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.berlin", "name": "Berlin, Germany", "x": 9682.941, "z": -10721.3594, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "switzerland.bern", "name": "Bern, Switzerland", "x": -13180.9141, "z": 19609.9766, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.bialystok", "name": "Białystok, Poland", "x": 43598.27, "z": -15603.52, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.bilbao", "name": "Bilbao, Spain", "x": -58855.082, "z": 32583.2656, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.birmingham", "name": "Birmingham, United Kingdom", "x": -46451.25, "z": -20943.125, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.bologna", "name": "Bologna, Italy", "x": 219.988281, "z": 33482.82, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.bordeaux", "name": "Bordeaux, France", "x": -46188.6875, "z": 27204.27, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "romania.brasov", "name": "Brașov, Romania", "x": 58002.2344, "z": 23332.7227, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "slovakia.bratislava", "name": "Bratislava, Slovakia", "x": 24023.1719, "z": 14410.8945, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.bremen", "name": "Bremen, Germany", "x": -4970.53125, "z": -14856.2617, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.brest", "name": "Brest, France", "x": -57421.54, "z": 3199.17969, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "belgium.brussel", "name": "Brussel, Belgium", "x": -22026.1719, "z": -3705.15625, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "czechrepublic.brno", "name": "Brno, Czech Republic", "x": 21873.7148, "z": 8794.824, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "romania.bucuresti", "name": "București, Romania", "x": 60720.85, "z": 31233.5, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "hungary.budapest", "name": "Budapest, Hungary", "x": 31817.6953, "z": 17362.5977, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "bulgaria.burgas", "name": "Burgas, Bulgaria", "x": 66797.05, "z": 39860.543, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.burgos", "name": "Burgos, Spain", "x": -62334.11, "z": 37141.07, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.cagliari", "name": "Cagliari, Italy", "x": -10160.8555, "z": 64051.8164, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.calais", "name": "Calais, France", "x": -31140.5273, "z": -5505.76563, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.calvi", "name": "Calvi, France", "x": -10635.9688, "z": 45497.4, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.cambridge", "name": "Cambridge, United Kingdom", "x": -37322.8125, "z": -16539.5234, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.cardiff", "name": "Cardiff, United Kingdom", "x": -54555.4023, "z": -15118.57, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.carlisle", "name": "Carlisle, United Kingdom", "x": -46439.3, "z": -40093.6, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.catania", "name": "Catania, Italy", "x": 16420.7148, "z": 74982.42, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.catanzaro", "name": "Catanzaro, Italy", "x": 23291.6563, "z": 66425.76, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.clermont-ferrand", "name": "Clermont-Ferrand, France", "x": -31047.5742, "z": 24228.3125, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "romania.cluj-napoca", "name": "Cluj-Napoca, Romania", "x": 49028.207, "z": 17957.05, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "portugal.coimbra", "name": "Coimbra, Portugal", "x": -87901.56, "z": 43976.832, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "romania.constanta", "name": "Constanța, Romania", "x": 71381.54, "z": 30500.7344, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.cordoba", "name": "Córdoba, Spain", "x": -74402.16, "z": 61412.9, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "romania.craiova", "name": "Craiova, Romania", "x": 50918.418, "z": 32508.39, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "latvia.daugavpils", "name": "Daugavpils, Latvia", "x": 52325.2773, "z": -32925.78, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "hungary.debrecen", "name": "Debrecen, Hungary", "x": 41291.4531, "z": 16863.582, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.dijon", "name": "Dijon, France", "x": -22820.1523, "z": 16285.375, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.dortmund", "name": "Dortmund, Germany", "x": -11102.1914, "z": -6914.77734, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.dover", "name": "Dover, United Kingdom", "x": -33772.0742, "z": -8554.48, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.dresden", "name": "Dresden, Germany", "x": 11926.2813, "z": -2164.55469, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.duisburg", "name": "Duisburg, Germany", "x": -13663.7188, "z": -6978.492, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.dusseldorf", "name": "Düsseldorf, Germany", "x": -13977.3047, "z": -4719.72656, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.edinburgh", "name": "Edinburgh, United Kingdom", "x": -45400.8672, "z": -47889.7969, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "turkey.edirne", "name": "Edirne, Turkey", "x": 64295.918, "z": 46409.043, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.erfurt", "name": "Erfurt, Germany", "x": 2172.01563, "z": -2117.94922, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.felixstowe", "name": "Felixstowe, United Kingdom", "x": -31964.6836, "z": -14857.3438, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.firenze", "name": "Firenze, Italy", "x": 581.625, "z": 38367.7734, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.frankfurtammain", "name": "Frankfurt am Main, Germany", "x": -6333.465, "z": 2531.73438, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "romania.galati", "name": "Galați, Romania", "x": 66046.03, "z": 23352.875, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.gdansk", "name": "Gdańsk, Poland", "x": 27642.9727, "z": -21539.6641, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "switzerland.geneve", "name": "Genève, Switzerland", "x": -18549.2578, "z": 23246.8945, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.genova", "name": "Genova, Italy", "x": -9232.379, "z": 34875.9766, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.glasgow", "name": "Glasgow, United Kingdom", "x": -51134.8242, "z": -49241.7461, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.goteborg", "name": "Göteborg, Sweden", "x": 6835.76172, "z": -40547.6172, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "austria.graz", "name": "Graz, Austria", "x": 18210.99, "z": 19941.7, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.grimsby", "name": "Grimsby, United Kingdom", "x": -36868.0234, "z": -27345.3086, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "netherlands.groningen", "name": "Groningen, Netherlands", "x": -12787.7578, "z": -15988.7813, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.hamburg", "name": "Hamburg, Germany", "x": -1826.84375, "z": -17158.3086, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.hannover", "name": "Hannover, Germany", "x": -3001.80322, "z": -10199.2979, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.helsingborg", "name": "Helsingborg, Sweden", "x": 9005.078, "z": -30502.55, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "finland.helsinki", "name": "Helsinki, Finland", "x": 44470.2266, "z": -56161.6328, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "romania.iasi", "name": "Iași, Romania", "x": 63246.293, "z": 13443.7422, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "austria.innsbruck", "name": "Innsbruck, Austria", "x": 1710.82813, "z": 19182.43, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "turkey.istanbul", "name": "İstanbul, Turkey", "x": 73653.375, "z": 45623.83, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.jonkoping", "name": "Jönköping, Sweden", "x": 13877.1367, "z": -40045.72, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "russia.kaliningrad", "name": "Kaliningrad, Russia", "x": 34315.05, "z": -23251.5039, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.kalmar", "name": "Kalmar, Sweden", "x": 19959.36, "z": -34554.6, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.karlskrona", "name": "Karlskrona, Sweden", "x": 16745.4336, "z": -31232.5234, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "lithuania.kaunas", "name": "Kaunas, Lithuania", "x": 44413.8828, "z": -26267.8555, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.kassel", "name": "Kassel, Germany", "x": -3381.44531, "z": -4418.828, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.katowice", "name": "Katowice, Poland", "x": 30278.66, "z": 1988.70313, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.kiel", "name": "Kiel, Germany", "x": -312.050781, "z": -21220.8477, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "austria.klagenfurtamworthersee", "name": "Klagenfurt am Wörthersee, Austria", "x": 13296.98, "z": 22755.7656, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "lithuania.klaipeda", "name": "Klaipėda, Lithuania", "x": 35592.6875, "z": -29939.6875, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "denmark.kobenhavn", "name": "København, Denmark", "x": 6800.617, "z": -28717.9063, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.koln", "name": "Köln, Germany", "x": -13750.918, "z": -3352.879, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "slovakia.kosice", "name": "Košice, Slovakia", "x": 39343.793, "z": 9974.258, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "finland.kotka", "name": "Kotka, Finland", "x": 49619.93, "z": -58615.79, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "finland.kouvola", "name": "Kouvola, Finland", "x": 48376.125, "z": -60829.0742, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.krakow", "name": "Kraków, Poland", "x": 33970.125, "z": 2757.55078, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "norway.kristiansand", "name": "Kristiansand, Norway", "x": -4788.40234, "z": -43061.625, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "finland.lahti", "name": "Lahti, Finland", "x": 45129.68, "z": -61177.1445, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.larochelle", "name": "La Rochelle, France", "x": -46580.87, "z": 19507.4219, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.leipzig", "name": "Leipzig, Germany", "x": 6649.0, "z": -3503.957, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.lehavre", "name": "Le Havre, France", "x": -39044.293, "z": 845.3594, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.lemans", "name": "Le Mans, France", "x": -40249.8633, "z": 9198.309, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "belgium.liege", "name": "Liège, Belgium", "x": -17581.6484, "z": -1501.37891, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "latvia.liepaja", "name": "Liepāja, Latvia", "x": 34204.3672, "z": -34145.0625, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.lille", "name": "Lille, France", "x": -26839.5156, "z": -2930.40625, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.limoges", "name": "Limoges, France", "x": -37817.4023, "z": 23211.8555, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.linkoping", "name": "Linköping, Sweden", "x": 17511.5469, "z": -43713.0273, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "austria.linz", "name": "Linz, Austria", "x": 12886.2656, "z": 13343.457, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "portugal.lisboa", "name": "Lisboa, Portugal", "x": -93310.5156, "z": 49853.3438, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.liverpool", "name": "Liverpool, United Kingdom", "x": -49621.86, "z": -29861.957, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.livorno", "name": "Livorno, Italy", "x": -2968.42188, "z": 39681.6836, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.lodz", "name": "Łódź, Poland", "x": 31264.3281, "z": -6664.043, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.london", "name": "London, United Kingdom", "x": -40196.9922, "z": -12259.34, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.lublin", "name": "Lublin, Poland", "x": 42744.07, "z": -4625.086, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "russia.luga", "name": "Luga, Russia", "x": 59346.33, "z": -50665.293, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "luxembourg.luxembourg", "name": "Luxembourg, Luxembourg", "x": -16384.34, "z": 3937.84766, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.lyon", "name": "Lyon, France", "x": -24477.9531, "z": 24957.9023, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.madrid", "name": "Madrid, Spain", "x": -65897.78, "z": 48202.9258, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.magdeburg", "name": "Magdeburg, Germany", "x": 4026.879, "z": -8242.57, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.malaga", "name": "Málaga, Spain", "x": -74294.31, "z": 68209.875, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.malmo", "name": "Malmö, Sweden", "x": 10234.7344, "z": -28001.293, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.manchester", "name": "Manchester, United Kingdom", "x": -46298.7773, "z": -28585.1445, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.mannheim", "name": "Mannheim, Germany", "x": -8322.992, "z": 5545.828, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.marseille", "name": "Marseille, France", "x": -24222.5313, "z": 38440.668, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.messina", "name": "Messina, Italy", "x": 17975.7422, "z": 70539.16, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.metz", "name": "Metz, France", "x": -16594.625, "z": 7093.59, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.milano", "name": "Milano, Italy", "x": -7916.57031, "z": 28693.5625, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.montpellier", "name": "Montpellier, France", "x": -30502.4883, "z": 35532.4922, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.munchen", "name": "München, Germany", "x": 2859.25, "z": 13848.9023, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.murcia", "name": "Murcia, Spain", "x": -56501.8438, "z": 64632.65, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.nantes", "name": "Nantes, France", "x": -47221.0742, "z": 13091.9219, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.napoli", "name": "Napoli, Italy", "x": 12418.1016, "z": 55071.93, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.newcastle-upon-tyne", "name": "Newcastle-upon-Tyne, United Kingdom", "x": -40128.168, "z": -39307.8438, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.nice", "name": "Nice, France", "x": -15870.4922, "z": 37786.04, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.nurnberg", "name": "Nürnberg, Germany", "x": 2028.10156, "z": 5855.76172, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "denmark.odense", "name": "Odense, Denmark", "x": 1017.5625, "z": -27270.543, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.olbia", "name": "Olbia, Italy", "x": -7765.93359, "z": 54715.4063, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.olsztyn", "name": "Olsztyn, Poland", "x": 34258.4727, "z": -18406.0664, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.orebro", "name": "Örebro, Sweden", "x": 16587.707, "z": -48894.8438, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "norway.oslo", "name": "Oslo, Norway", "x": 4140.789, "z": -53680.668, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.osnabruck", "name": "Osnabrück, Germany", "x": -8120.60547, "z": -9933.598, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "czechrepublic.ostrava", "name": "Ostrava, Czech Republic", "x": 27831.8125, "z": 4715.97656, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.palermo", "name": "Palermo, Italy", "x": 8350.891, "z": 70487.19, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "lithuania.panevezys", "name": "Panevėžys, Lithuania", "x": 45652.2031, "z": -30282.9375, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.paris", "name": "Paris, France", "x": -31427.4727, "z": 6366.074, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "estonia.parnu", "name": "Pärnu, Estonia", "x": 44076.6445, "z": -45757.83, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "hungary.pecs", "name": "Pécs, Hungary", "x": 28439.8047, "z": 25941.5234, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.pescara", "name": "Pescara, Italy", "x": 12397.9961, "z": 46327.97, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "romania.pitesti", "name": "Pitești, Romania", "x": 55747.4141, "z": 29392.3711, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "bulgaria.pleven", "name": "Pleven, Bulgaria", "x": 56844.457, "z": 37037.4258, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "bulgaria.plovdiv", "name": "Plovdiv, Bulgaria", "x": 56984.668, "z": 44949.293, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.plymouth", "name": "Plymouth, United Kingdom", "x": -60566.5, "z": -8502.445, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "finland.pori", "name": "Pori, Finland", "x": 34762.21, "z": -61827.7578, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "portugal.porto", "name": "Porto, Portugal", "x": -86461.77, "z": 38180.2, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.poznan", "name": "Poznań, Poland", "x": 22313.2773, "z": -9682.324, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "czechrepublic.praha", "name": "Praha, Czech Republic", "x": 13699.582, "z": 3458.84766, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "russia.pskov", "name": "Pskov, Russia", "x": 55868.2, "z": -44822.4922, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.reims", "name": "Reims, France", "x": -24104.89, "z": 5610.01563, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.rennes", "name": "Rennes, France", "x": -47239.95, "z": 7144.48438, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "latvia.rezekne", "name": "Rēzekne, Latvia", "x": 54948.31, "z": -36100.7422, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "latvia.riga", "name": "Rīga, Latvia", "x": 43827.875, "z": -37984.81, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.roma", "name": "Roma, Italy", "x": 5511.125, "z": 48579.21, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.rostock", "name": "Rostock, Germany", "x": 5990.824, "z": -19109.05, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "netherlands.rotterdam", "name": "Rotterdam, Netherlands", "x": -20456.0781, "z": -9455.93, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "bulgaria.ruse", "name": "Ruse, Bulgaria", "x": 60953.87, "z": 34599.6328, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "russia.saintpetersburg", "name": "Saint Petersburg, Russia", "x": 59623.6953, "z": -57210.7734, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.salamanca", "name": "Salamanca, Spain", "x": -73525.99, "z": 43417.7031, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "austria.salzburg", "name": "Salzburg, Austria", "x": 8519.496, "z": 15274.625, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.sassari", "name": "Sassari, Italy", "x": -11556.4141, "z": 55186.8633, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.sevilla", "name": "Sevilla, Spain", "x": -80651.09, "z": 62085.91, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.sheffield", "name": "Sheffield, United Kingdom", "x": -43088.88, "z": -27107.6914, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "lithuania.siauliai", "name": "Šiauliai, Lithuania", "x": 42563.6328, "z": -31373.9414, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "bulgaria.sofia", "name": "Sofia, Bulgaria", "x": 50404.66, "z": 41995.52, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.southampton", "name": "Southampton, United Kingdom", "x": -46838.8672, "z": -7893.371, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "norway.stavanger", "name": "Stavanger, Norway", "x": -10808.8164, "z": -48421.8945, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.strasbourg", "name": "Strasbourg, France", "x": -11387.07, "z": 10537.2656, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.stockholm", "name": "Stockholm, Sweden", "x": 24368.4766, "z": -48316.2227, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "germany.stuttgart", "name": "Stuttgart, Germany", "x": -5607.965, "z": 9426.875, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "unitedkingdom.swansea", "name": "Swansea, United Kingdom", "x": -57646.13, "z": -17652.07, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "hungary.szeged", "name": "Szeged, Hungary", "x": 36318.0938, "z": 23928.0742, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.szczecin", "name": "Szczecin, Poland", "x": 14502.5352, "z": -15569.8906, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "estonia.tallinn", "name": "Tallinn, Estonia", "x": 43213.3633, "z": -51613.7539, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "finland.tampere", "name": "Tampere, Finland", "x": 40138.7227, "z": -62610.8672, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.taranto", "name": "Taranto, Italy", "x": 25490.4258, "z": 57821.28, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "romania.targumures", "name": "Târgu Mureș, Romania", "x": 52709.5547, "z": 19237.0742, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "estonia.tartu", "name": "Tartu, Estonia", "x": 50707.88, "z": -46878.1367, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "turkey.tekirdag", "name": "Tekirdağ, Turkey", "x": 68190.42, "z": 48967.668, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "romania.timisoara", "name": "Timișoara, Romania", "x": 40552.2148, "z": 26307.9023, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.torino", "name": "Torino, Italy", "x": -13222.375, "z": 30211.8828, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "france.toulouse", "name": "Toulouse, France", "x": -40063.3828, "z": 34895.46, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "finland.turku", "name": "Turku, Finland", "x": 36022.72, "z": -56376.15, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.uppsala", "name": "Uppsala, Sweden", "x": 23521.3281, "z": -52104.625, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.valencia", "name": "València, Spain", "x": -52433.26, "z": 56537.1328, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.valladolid", "name": "Valladolid, Spain", "x": -68298.24, "z": 40437.5625, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "latvia.valmiera", "name": "Valmiera, Latvia", "x": 47622.93, "z": -41103.87, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "bulgaria.varna", "name": "Varna, Bulgaria", "x": 69393.3, "z": 35442.1055, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.vasteras", "name": "Västerås, Sweden", "x": 20562.6016, "z": -50738.4336, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "sweden.vaxjo", "name": "Växjö, Sweden", "x": 15519.2773, "z": -35205.69, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.venezia", "name": "Venezia, Italy", "x": 4689.758, "z": 29658.8047, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "italy.verona", "name": "Verona, Italy", "x": -461.015625, "z": 28983.2, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.vigo", "name": "Vigo, Spain", "x": -85371.51, "z": 31880.5586, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "lithuania.vilnius", "name": "Vilnius, Lithuania", "x": 49462.4375, "z": -25905.7852, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.warszawa", "name": "Warszawa, Poland", "x": 36644.79, "z": -10355.9609, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "austria.wien", "name": "Wien, Austria", "x": 19939.6328, "z": 13465.9063, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "poland.wroclaw", "name": "Wrocław, Poland", "x": 22802.7734, "z": -3021.10547, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "spain.zaragoza", "name": "Zaragoza, Spain", "x": -51574.5234, "z": 43273.8945, "price": 100000, "base_slots": 3, "slot_price": 10000}, {"id": "switzerland.zurich", "name": "Zürich, Switzerland", "x": -8773.934, "z": 17498.34, "price": 100000, "base_slots": 3, "slot_price": 10000}],
        "truck_refund": 0.3,
        "scrap_refund": 0.1,
        "garage_refund": 0.5,
        "slot_refund": 0.5,

        "currency_name": "coin",
        "usd_to_coin": 0.5,
        "eur_to_coin": 0.6,
        "wear_ratio": 1,
        "revenue_share_to_company": 0.4,
        "truck_rental_cost": 0.01,

        "max_wear_before_service": 0.1,
        "max_distance_before_scrap": 500000,
        "unit_service_price": 1200,

        "allow_purchase_truck": True,
        "allow_purchase_garage": True,
        "allow_purchase_slot": True,
        "enable_balance_leaderboard": True
    },

    "perms": {
        "admin": [0],
        "config": [],
        "reload_config": [],
        "restart": [],

        "hrm": [],
        "disable_user_mfa": [],
        "update_user_discord": [],
        "delete_account_connections": [],
        "delete_user": [],
        "update_application_positions": [],
        "delete_dlog": [],

        "hr": [],
        "manage_profile": [],
        "add_member": [],
        "update_member_roles": [],
        "update_member_points": [],
        "dismiss_member": [],
        "get_pending_user_list": [],
        "delete_application": [],
        "ban_user": [],

        "economy_manager": [],
        "balance_manager": [],
        "accountant": [],
        "truck_manager": [],
        "garage_manager": [],

        "audit": [],
        "announcement": [],
        "challenge": [],
        "division": [],
        "downloads": [],
        "event": [],
        
        "driver": [100]
    },

    "roles": [
        {"id": 0, "name": "root", "color": "#000000"}
    ],

    "webhook_audit": ""
}

def validateConfig(cfg):
    if not "hex_color" in cfg.keys():
        cfg["hex_color"] = "2fc1f7"
    hex_color = cfg["hex_color"][-6:]
    try:
        # validate color
        tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        int(hex_color, 16) # try initify
    except:
        hex_color = "2fc1f7"
        cfg["hex_color"] = "2fc1f7"

    if not "perms" in cfg.keys():
        cfg["perms"] = default_config["perms"]
    perms = cfg["perms"]
    for perm in perms.keys():
        roles = perms[perm]
        newroles = []
        try:
            for role in roles:
                try:
                    newroles.append(int(role))
                except:
                    pass
        except:
            pass
        perms[perm] = newroles
    cfg["perms"] = perms

    if not "roles" in cfg.keys():
        cfg["roles"] = default_config["roles"]
    roles = cfg["roles"]
    newroles = []
    for i in range(len(roles)):
        role = roles[i]
        try:
            role["id"] = int(role["id"])
        except:
            continue
        if "id" in role.keys() and "name" in role.keys():
            newroles.append(role)
    cfg["roles"] = newroles

    if not "ranks" in cfg.keys():
        cfg["ranks"] = default_config["ranks"]
    ranks = cfg["ranks"]
    newranks = []
    for i in range(len(ranks)):
        rank = ranks[i]
        if "distance" in rank.keys():
            rank["points"] = rank["distance"]
            del rank["distance"]
        try:
            rank["points"] = int(rank["points"])
        except:
            continue
        try:
            int(rank["discord_role_id"])
            # just validation, no need t oconvert, as discord_role_id is not mandatory
        except:
            rank["discord_role_id"] = None
        if "discord_role_id" in rank.keys() and "points" in rank.keys() and "name" in rank.keys():
            newranks.append(rank)
    cfg["ranks"] = newranks

    if not "divisions" in cfg.keys():
        cfg["divisions"] = default_config["divisions"]
    divisions = cfg["divisions"]
    newdivisions = []
    for i in range(len(divisions)):
        division = divisions[i]
        if "point" in division.keys():
            division["points"] = division["point"]
            del division["point"]
        if "id" in division.keys() and "name" in division.keys() and "role_id" in division.keys() and "points" in division.keys():
            try:
                division["id"] = int(division["id"])
                division["role_id"] = int(division["role_id"])
                division["points"] = min(int(division["points"]), 2147483647)
                newdivisions.append(division)
            except:
                pass
    cfg["divisions"] = newdivisions
    
    if not "economy" in cfg.keys():
        cfg["economy"] = default_config["economy"]

    economy_trucks = cfg["economy"]["trucks"]
    new_economy_trucks = []
    for i in range(len(economy_trucks)):
        truck = economy_trucks[i]
        if "id" in truck.keys() and "brand" in truck.keys() and "model" in truck.keys() and "price" in truck.keys():
            try:
                truck["id"] = truck["id"][len("vehicle."):] if truck["id"].startswith("vehicle.") else truck["id"]
                truck["price"] = min(int(truck["price"]), 4294967296)
            except:
                pass
            new_economy_trucks.append(truck)
    cfg["economy"]["trucks"] = new_economy_trucks
    
    economy_garages = cfg["economy"]["garages"]
    new_economy_garages = []
    for i in range(len(economy_garages)):
        garage = economy_garages[i]
        if "id" in garage.keys() and "name" in garage.keys() and "x" in garage.keys() and "z" in garage.keys() and "price" in garage.keys() and "base_slots" in garage.keys() and "slot_price" in garage.keys():
            try:
                garage["x"] = float(garage["x"])
                garage["z"] = float(garage["z"])
                garage["price"] = min(int(garage["price"]), 4294967296)
                garage["base_slots"] = min(int(garage["base_slots"]), 10)
                garage["slot_price"] = min(int(garage["slot_price"]), 4294967296)
            except:
                pass
            new_economy_garages.append(garage)
    cfg["economy"]["garages"] = new_economy_garages

    economy_must_float = ['truck_refund', 'scrap_refund', 'garage_refund', 'slot_refund', 'usd_to_coin', 'eur_to_coin', 'wear_ratio', 'revenue_share_to_company', 'truck_rental_cost', 'max_wear_before_service', 'max_distance_before_scrap', 'unit_service_price']
    for item in economy_must_float:
        if not item in cfg["economy"].keys() or not isfloat(cfg["economy"][item]):
            cfg["economy"][item] = default_config["economy"][item]
        else:
            cfg["economy"][item] = float(cfg["economy"][item])

    economy_must_bool = ['allow_purchase_truck', 'allow_purchase_garage', 'allow_purchase_slot', 'enable_balance_leaderboard']
    for item in economy_must_bool:
        if not item in cfg["economy"].keys() or type(cfg["economy"][item]) != bool:
            cfg["economy"][item] = default_config["economy"][item]
    
    if not "currency_name" in cfg["economy"].keys():
        cfg["economy"]["currency_name"] = "coin"

    if not "application_types" in cfg.keys():
        cfg["application_types"] = default_config["application_types"]
    application_types = cfg["application_types"]
    new_application_types = []
    reqs = ["id", "name", "discord_role_id", "staff_role_id", "message", "webhook", "note"]
    for i in range(len(application_types)):
        application_type = application_types[i]
        try:
            application_type["id"] = int(application_type["id"])
            for i in range(len(application_type["staff_role_id"])):
                application_type["staff_role_id"][i] = int(application_type["staff_role_id"][i])
        except:
            continue
        try:
            int(application_type["discord_role_id"])
            # just validation, no need t oconvert, as discord_role_id is not mandatory
        except:
            application_type["discord_role_id"] = None
        ok = True
        for req in reqs:
            if not req in application_type.keys():
                ok = False
        if ok:
            new_application_types.append(application_type)
    cfg["application_types"] = new_application_types
    
    if not "external_plugins" in cfg.keys():
        cfg["external_plugins"] = default_config["external_plugins"]
    external_plugins = cfg["external_plugins"]
    new_external_plugins = []
    for plugin in external_plugins:
        if plugin.replace(" ","") != "":
            new_external_plugins.append(plugin)
    cfg["external_plugins"] = new_external_plugins

    try:
        cfg["mysql_pool_size"] = int(cfg["mysql_pool_size"])
    except:
        cfg["mysql_pool_size"] = 10

    # renamed configs
    if "apidoc" in cfg.keys():
        cfg["openapi"] = cfg["apidoc"]
        del cfg["apidoc"]

    if "allowed_navio_ips" in cfg.keys():
        cfg["allowed_tracker_ips"] = cfg["allowed_navio_ips"]
        del cfg["allowed_navio_ips"]

    if not "member_accept" in cfg.keys() and "team_update" in cfg.keys():
        cfg["member_accept"] = cfg["team_update"]
        del cfg["team_update"]
    
    if not "discord_callback" in cfg["frontend_urls"].keys():
        cfg["frontend_urls"]["discord_callback"] = f"https://{cfg['domain']}/connectDiscord"
    
    if not "email_confirm" in cfg["frontend_urls"].keys():
        cfg["frontend_urls"]["email_confirm"] = f"https://{cfg['domain']}/emailConfirm?secret={{secret}}"

    if not "server_host" in cfg.keys() and "server_ip" in cfg.keys():
        cfg["server_host"] = cfg["server_ip"]
        del cfg["server_ip"]
    
    # v2.4.4
    if not "plugins" in cfg.keys() and "enabled_plugins" in cfg.keys():
        cfg["plugins"] = cfg["enabled_plugins"]
        del cfg["enabled_plugins"]

    tcfg = {}
    for key in config_keys_order:
        if key in cfg.keys():
            tcfg[key] = cfg[key]
        else:
            tcfg[key] = default_config[key]

    return tcfg