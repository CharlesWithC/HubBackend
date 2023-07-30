# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import hashlib
import os
import string
import time
import unicodedata
from io import BytesIO

import aiohttp
import psutil
import requests
from fastapi import Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image, ImageDraw, ImageFont

# to get supported_glyph_ord_range, run the following code
#
# from fontTools.ttLib import TTFont
# font = TTFont("./font.ttf")
# d = []
# for table in font['cmap'].tables:
#     for key in table.cmap.keys():
#         if not key in d:
#             d.append(key)
# d = sorted(d)
# r = []
# st = d[0]
# for i in range(1, len(d)):
#     if d[i] - d[i-1] > 1:
#         if d[i-1] == st:
#             r.append(st)
#         else:
#             r.append((st, d[i-1]))
#         st = d[i]
# if d[len(d) - 1] == st:
#     r.append(st)
# else:
#     r.append((st, d[len(d)-1]))
# supported_glyph_ord_range = r

# UbuntuMono.ttf
supported_glyph_ord_range = [0, (8, 9), 13, 29, (32, 126), (128, 591), 658, 700, (710, 711), 713, (728, 733), 785, (900, 902), (904, 906), 908, (910, 929), (931, 974), (1024, 1119), (1122, 1123), (1138, 1141), (1162, 1273), (7808, 7813), (7922, 7923), (7936, 7957), (7960, 7965), (7968, 8005), (8008, 8013), (8016, 8023), 8025, 8027, 8029, (8031, 8061), (8064, 8116), (8118, 8132), (8134, 8147), (8150, 8155), (8157, 8175), (8178, 8180), (8182, 8190), (8211, 8213), (8216, 8218), (8220, 8222), (8224, 8226), 8230, 8240, (8249, 8250), 8260, 8304, (8308, 8313), (8320, 8329), 8364, 8366, 8372, 8377, 8467, 8470, 8482, 8486, 8494, (8531, 8542), 8706, 8710, 8719, (8721, 8722), 8725, (8729, 8730), 8734, 8747, 8776, 8800, (8804, 8805), 9472, 9474, 9484, 9488, 9492, 9496, 9500, 9508, 9516, 9524, 9532, (9552, 9580), 9608, (9617, 9619), 9674, 57599, 61437, (61440, 61442), (62726, 62737), (63498, 63517), (64257, 64258), 65533]
supported_glyph_ord = []
for i in supported_glyph_ord_range:
    if type(i) == int:
        supported_glyph_ord.append(i)
    elif type(i) == tuple:
        for j in range(i[0],i[1]+1):
            supported_glyph_ord.append(j)

def has_glyph(glyph):
    if ord(glyph) in supported_glyph_ord:
        return True
    return False

# Due to the nature of UbuntuMono font family has same width for all characters
# We can preload its wsize to prevent using .getsize() which is slow
# NOTE that non-printable characters from Sans Serif will still need .getsize()
ubuntu_mono_bold_font_wsize = []
for i in range(1, 81):
    font = ImageFont.truetype("./fonts/UbuntuMonoBold.ttf", i)
    wsize = font.getlength("a")
    ubuntu_mono_bold_font_wsize.append(wsize)
del font

class arequests():
    async def get(url, data = None, headers = None, timeout = 10):
        async with aiohttp.ClientSession(trust_env = True) as session:
            async with session.get(url, data = data, headers = headers, timeout = timeout) as resp:
                r = requests.Response()
                r.status_code = resp.status
                r._content = await resp.read()
                return r

async def get_banner(request: Request, response: Response):
    try:
        process = psutil.Process()
        sleep_cnt = 0
        while process.memory_info().rss / 1024 / 1024 > request.app.memory_threshold and request.app.memory_threshold != 0:
            sleep_cnt += 0.1
            await asyncio.sleep(0.1)
            if sleep_cnt >= 30:
                return JSONResponse({"error": "Service Unavailable"}, status_code = 503)
    except:
        return JSONResponse({"error": "Service Unavailable"}, status_code = 503)

    request_start_time = time.time()

    data = await request.json()
    company_abbr = data["company_abbr"]
    company_name = data["company_name"]
    company_name = unicodedata.normalize('NFKC', company_name).upper()
    logo_url = data["logo_url"]
    hex_color = data["hex_color"][-6:]
    userid = data["userid"]

    try:
        # validate color
        tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        int(hex_color, 16)
    except:
        hex_color = "2fc1f7"

    for fi in os.listdir("/tmp/hub/banner"):
        if time.time() - os.path.getmtime(f"/tmp/hub/banner/{fi}") > 1800:
            os.remove(f"/tmp/hub/banner/{fi}")

    if os.path.exists(f"/tmp/hub/banner/{company_abbr}_{userid}.png"):
        if time.time() - os.path.getmtime(f"/tmp/hub/banner/{company_abbr}_{userid}.png") <= 600:
            response = StreamingResponse(iter([open(f"/tmp/hub/banner/{company_abbr}_{userid}.png","rb").read()]), media_type="image/jpeg")
            return response

    logo = Image.new("RGBA", (200,200),(255,255,255))
    banner = Image.new("RGB", (1700,300),(255,255,255))

    if os.path.exists(f"/tmp/hub/logo/{company_abbr}.png") and os.path.exists(f"/tmp/hub/template/{company_abbr}.png") and \
            time.time() - os.path.getmtime(f"/tmp/hub/logo/{company_abbr}.png") <= 86400: # update everyday
        logo = Image.open(f"/tmp/hub/logo/{company_abbr}.png")
        banner = Image.open(f"/tmp/hub/template/{company_abbr}.png")
    else:
        try:
            right = await arequests.get(logo_url, timeout = 5)

            if right.status_code == 200:
                logo = right.content
                del right
                if len(logo) / (1024 * 1024) > 10:
                    raise MemoryError("Logo too large. Aborted.")
                logo = Image.open(BytesIO(logo))
                logobbox = logo.getbbox()
                if logobbox[3] - logobbox[1] > 3400 or logobbox[2] - logobbox[0] > 3400:
                    raise MemoryError("Logo too large. Aborted.")
                if logobbox[3] - logobbox[1] > 1700 or logobbox[2] - logobbox[0] > 1700:
                    logo = logo.resize((1700, 1700), resample=Image.Resampling.LANCZOS).convert("RGBA")
                else:
                    logo = logo.convert("RGBA")
                logo_large = logo # to copy properties
                logo_datas = logo.getdata()
                logo_large_datas = []
                for item in logo_datas:
                    if item[3] == 0:
                        logo_large_datas.append((255,255,255))
                    else:
                        logo_large_datas.append((int(0.85*255+0.15*item[3]/255*item[0]), \
                            int(0.85*255+0.15*item[3]/255*item[1]), int(0.85*255+0.15*item[3]/255*item[2])))
                    # use 85% transparent logo for background (with white background)
                logo = logo.resize((200, 200), resample=Image.Resampling.LANCZOS).convert("RGBA")
                logo.save(f"/tmp/hub/logo/{company_abbr}.png", optimize = True)
                logo_datas = logo.getdata()

                logo_large.putdata(logo_large_datas)
                del logo_large_datas
                logo_large = logo_large.resize((1700, 1700), resample=Image.Resampling.LANCZOS).convert("RGB")

                # render logo
                banner = logo_large.crop((0, 700, 1700, 1000))
                del logo_large
                logo_bg = banner.crop((1475, 25, 1675, 225))
                datas = list(logo_bg.getdata())
                for i in range(0,200):
                    for j in range(0,200):
                        # paste avatar
                        if logo_datas[i*200+j][3] == 255:
                            datas[i*200+j] = logo_datas[i*200+j]
                        elif logo_datas[i*200+j][3] != 0:
                            bg_a = 1 - logo_datas[i*200+j][3] / 255
                            fg_a = logo_datas[i*200+j][3] / 255
                            bg = datas[i*200+j]
                            fg = logo_datas[i*200+j]
                            datas[i*200+j] = (int(bg[0]*bg_a+fg[0]*fg_a), int(bg[1]*bg_a+fg[1]*fg_a), int(bg[2]*bg_a+fg[2]*fg_a))
                logo_bg.putdata(datas)
                banner.paste(logo_bg, (1475, 25, 1675, 225))
                del logo_bg, logo_datas, datas

        except:
            logo = Image.new("RGBA", (200,200),(255,255,255))
            banner = Image.new("RGB", (1700,300),(255,255,255))

        # draw company name
        draw = ImageDraw.Draw(banner)
        usH45 = ImageFont.truetype("./fonts/OpenSansExtraBold.ttf", 45)
        theme_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        company_name_len = usH45.getlength(f"{company_name}")
        draw.text((1700 - 20 - company_name_len, 235), f"{company_name}", fill=theme_color, font=usH45)
        del draw, usH45

        banner.save(f"/tmp/hub/template/{company_abbr}.png", optimize = True)

    avatar = data["avatar"]
    avatarh = hashlib.sha256(avatar.encode()).hexdigest()[:16]

    for fi in os.listdir("/tmp/hub/avatar"):
        if len(fi.split("_")) != 3:
            os.remove(f"/tmp/hub/avatar/{fi}")
            continue

        lcompanyabbr = fi.split("_")[0]
        luserid = fi.split("_")[1]
        lavatarh = "_".join(fi.split("_")[2:]).split(".")[0]
        if lcompanyabbr == company_abbr and luserid == str(userid) and lavatarh != avatarh:
            # user changed avatar
            os.remove(f"/tmp/hub/avatar/{fi}")
            continue
        if lcompanyabbr == company_abbr and luserid == str(userid) and lavatarh == avatarh:
            # user didn't change avatar, and user is active, preserve avatar longer
            mtime = os.path.getmtime(f"/tmp/hub/avatar/{fi}")
            os.utime(f"/tmp/hub/avatar/{fi}", (time.time(), mtime))
        if time.time() - os.path.getatime(f"/tmp/hub/avatar/{fi}") > 86400 * 7:
            os.remove(f"/tmp/hub/avatar/{fi}")
            continue

    if os.path.exists(f"/tmp/hub/avatar/{company_abbr}_{userid}_{avatarh}.png"):
        avatar = Image.open(f"/tmp/hub/avatar/{company_abbr}_{userid}_{avatarh}.png")
    else:
        if str(avatar) == "None":
            avatar = logo.resize((250, 250)).convert("RGBA")
        else:
            # pre-process avatar
            try: # in case image is invalid
                right = await arequests.get(avatar, timeout = 5)
                if right.status_code == 200:
                    try:
                        if len(right.content) / (1024 * 1024) > 10:
                            raise MemoryError("Avatar too large. Aborted.")
                        avatar = Image.open(BytesIO(right.content))
                        avatarbbox = avatar.getbbox()
                        if avatarbbox[3] - avatarbbox[1] > 3400 or avatarbbox[2] - avatarbbox[0] > 3400:
                            raise MemoryError("Avatar too large. Aborted.")
                        avatar = avatar.resize((250, 250)).convert("RGBA")
                    except:
                        avatar = logo.resize((250, 250)).convert("RGBA")
                else:
                    avatar = logo.resize((250, 250)).convert("RGBA")
                del right
                def dist(a,b,c,d):
                    return (c-a)*(c-a)+(b-d)*(b-d)
                datas = avatar.getdata()
                newData = []
                for i in range(0,250):
                    for j in range(0,250):
                        if dist(i,j,125,125) > 125*125:
                            newData.append((255,255,255,0))
                        else:
                            newData.append(datas[i*250+j])
                avatar.putdata(newData)
                del datas, newData
                avatar.save(f"/tmp/hub/avatar/{company_abbr}_{userid}_{avatarh}.png", optimize = True)
            except:
                avatar = logo.resize((250, 250)).convert("RGBA")
    avatar = avatar.getdata()

    # render avatar
    avatar_bg = banner.crop((35, 25, 285, 275))
    datas = list(avatar_bg.getdata())
    for i in range(0,250):
        for j in range(0,250):
            # paste avatar
            if avatar[i*250+j][3] == 255:
                datas[i*250+j] = avatar[i*250+j]
            elif avatar[i*250+j][3] != 0:
                bg_a = 1 - avatar[i*250+j][3] / 255
                fg_a = avatar[i*250+j][3] / 255
                bg = datas[i*250+j]
                fg = avatar[i*250+j]
                datas[i*250+j] = (int(bg[0]*bg_a+fg[0]*fg_a), int(bg[1]*bg_a+fg[1]*fg_a), int(bg[2]*bg_a+fg[2]*fg_a))
    avatar_bg.putdata(datas)
    banner.paste(avatar_bg, (35, 25, 285, 275))
    del datas, avatar_bg

    # draw text
    draw = ImageDraw.Draw(banner)
    theme_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # draw name
    name = data["name"]
    name = unicodedata.normalize('NFKC', name).lstrip(" ")
    tname = ""
    all_printable = True
    for i in range(len(name)):
        if name[i] in string.printable:
            tname += name[i]
        elif has_glyph(name[i]):
            tname += name[i]
            all_printable = False
    name = tname

    left = 1
    right = 80
    fontsize = 80
    while right - left > 1:
        fontsize = (left + right) // 2
        if all_printable:
            namew = ubuntu_mono_bold_font_wsize[fontsize] * len(name)
        else:
            namefont = ImageFont.truetype("./fonts/UbuntuMonoBold.ttf", fontsize)
            namew = namefont.getlength(f"{name}")
        if namew > 450:
            right = fontsize - 1
        else:
            left = fontsize + 1
    namefont = ImageFont.truetype("./fonts/UbuntuMonoBold.ttf", fontsize)
    namebb = namefont.getbbox(f"{name}")
    nameh = namebb[3] - namebb[1]
    offset = min(fontsize * 0.05, 20)
    draw.text((325, 50 + offset - namebb[1]), name, fill=(0,0,0), font=namefont)
    del namefont
    # y = 50 ~ 70

    fontsize -= 20
    highest_role = data["highest_role"]
    highest_role = unicodedata.normalize('NFKC', highest_role).lstrip(" ")
    hrolefont = ImageFont.truetype("./fonts/Anton.ttf", fontsize)
    hrolew = hrolefont.getlength(f"{highest_role}")
    for _ in range(100):
        if hrolew > 450:
            fontsize -= 1
            hrolefont = ImageFont.truetype("./fonts/Anton.ttf", fontsize)
            hrolew = hrolefont.getlength(f"{highest_role}")
    hrolebb = hrolefont.getbbox(f"{highest_role}")
    hroleh = hrolebb[3] - hrolebb[1]

    nameb = 55 + offset + nameh
    joinedt = 210
    draw.text((325, (joinedt + nameb - hroleh) / 2 - hrolebb[1]), f"{highest_role}", fill=theme_color, font=hrolefont)
    del hrolefont
    # y = 115 ~ 155

    joined = data["joined"]
    division = data["division"]
    division = unicodedata.normalize('NFKC', division).lstrip(" ")
    distance = data["distance"]
    profit = data["profit"]
    joinedfont = ImageFont.truetype("./fonts/UbuntuMono.ttf", 40)
    draw.text((325, 220), f"Joined: {joined}", fill=(0,0,0), font=joinedfont)
    del joinedfont

    # separate line
    coH40 = ImageFont.truetype("./fonts/UbuntuMonoBold.ttf", 40)
    draw.line((850, 25, 850, 275), fill=theme_color, width = 10)
    divisionw = coH40.getlength(f"Division: {division}")
    if divisionw > 550:
        left = 1
        right = len(division)
        length = 0
        org_division = str(division)
        while right - left > 1:
            length = (left + right) // 2
            division = org_division[:length] + "..."
            divisionw = coH40.getlength(f"Division: {division}")
            if divisionw > 550:
                right = length
            else:
                left = length
        division = org_division[:length] + "..."
    draw.text((900, 50), f"Division: {division}", fill=(0,0,0), font=coH40)
    draw.text((900, 110), f"Distance: {distance}", fill=(0,0,0), font=coH40)
    draw.text((900, 170), f"Income: {profit}", fill=(0,0,0), font=coH40)
    del coH40

    # output
    output = BytesIO()
    banner.save(output, "jpeg", optimize = True)
    del banner, logo, avatar, draw
    open(f"/tmp/hub/banner/{company_abbr}_{userid}.png","wb").write(output.getvalue())

    response = StreamingResponse(iter([output.getvalue()]), media_type="image/jpeg")
    del output

    request_end_time = time.time()
    if request.app.enable_performance_header:
        response.headers["X-Response-Time"] = str(round(request_end_time - request_start_time, 4))

    return response
