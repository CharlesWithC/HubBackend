# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from PIL import Image, ImageFont, ImageDraw
import requests, os, time
from io import BytesIO
from datetime import datetime
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/banner")
async def banner(request: Request, response: Response):
    form = await request.form()
    company_abbr = form["company_abbr"]
    company_name = form["company_name"]
    logo_url = form["logo_url"]
    hex_color = form["hex_color"][-6:]
    discordid = form["discordid"]

    l = os.listdir(f"/tmp/hub/banner")
    for ll in l:
        if time.time() - os.path.getmtime(f"/tmp/hub/banner/{ll}") > 7200:
            os.remove(f"/tmp/hub/banner/{ll}")

    l = os.listdir(f"/tmp/hub/avatar")
    for ll in l:
        if time.time() - os.path.getmtime(f"/tmp/hub/avatar/{ll}") > 86400:
            os.remove(f"/tmp/hub/avatar/{ll}")

    if os.path.exists(f"/tmp/hub/banner/{company_abbr}_{discordid}.png"):
        if time.time() - os.path.getmtime(f"/tmp/hub/banner/{company_abbr}_{discordid}.png") <= 3600:
            response = StreamingResponse(iter([open(f"/tmp/hub/banner/{company_abbr}_{discordid}.png","rb").read()]), media_type="image/jpeg")
            return response

    logo = Image.new("RGBA", (200,200),(255,255,255))
    logobg = Image.new("RGB", (1700,1700),(255,255,255))

    if os.path.exists(f"/tmp/hub/logo/{company_abbr}.png"):
        logo = Image.open(f"/tmp/hub/logo/{company_abbr}.png").convert("RGBA")
        logobg = Image.open(f"/tmp/hub/logo/{company_abbr}_bg.png").convert("RGB")
    else:
        r = requests.get(logo_url, timeout = 3)
        if r.status_code == 200:
            logo = r.content
            try: # in case image is invalid
                logo = Image.open(BytesIO(logo)).convert("RGBA")
                logo = logo
                logobg = logo
                lnd = []
                lbnd = []
                datas = logo.getdata()
                for item in datas:
                    lnd.append(item) # use original logo for small one
                    if item[3] == 0:
                        lbnd.append((255,255,255,255))
                    else:
                        lbnd.append((int(0.85*255+0.15*item[3]/255*item[0]), \
                            int(0.85*255+0.15*item[3]/255*item[1]), int(0.85*255+0.15*item[3]/255*item[2]), 255))
                    # use 85% transparent logo for background (with white background)
                logo.putdata(lnd)
                logo = logo.resize((200, 200), resample=Image.ANTIALIAS).convert("RGBA")
                logobg.putdata(lbnd)
                logobg = logobg.resize((1700, 1700), resample=Image.ANTIALIAS).convert("RGB")

                logo.save(f"/tmp/hub/logo/{company_abbr}.png", optimize = True)
                logobg.save(f"/tmp/hub/logo/{company_abbr}_bg.png", optimize = True)
            except:
                pass

    avatar = form["avatar"]
    avatarid = avatar
    if os.path.exists(f"/tmp/hub/avatar/{discordid}_{avatar}.png"):
        avatar = Image.open(f"/tmp/hub/avatar/{discordid}_{avatar}.png")
    else:
        # pre-process avatar
        avatarurl = ""
        if avatar.startswith("a_"):
            avatarurl = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.gif"
        else:
            avatarurl = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.png"
        r = requests.get(avatarurl, timeout=3)
        try: # in case image is invalid
            usedefault = False
            if r.status_code == 200:
                try:
                    avatar = Image.open(BytesIO(r.content)).resize((250, 250)).convert("RGBA")
                except:
                    avatar = logo.resize((250, 250)).convert("RGBA")
            else:
                avatar = logo.resize((250, 250)).convert("RGBA")
            def dist(a,b,c,d):
                return (c-a)*(c-a)+(b-d)*(b-d)
            data = avatar.getdata()
            newData = []
            for i in range(0,250):
                for j in range(0,250):
                    if dist(i,j,125,125) > 125*125:
                        newData.append((255,255,255,0))
                    else:
                        newData.append(data[i*250+j])
            avatar.putdata(newData)
            avatar.save(f"/tmp/hub/avatar/{discordid}_{avatarid}.png", optimize = True)
        except:
            pass
    avatar = avatar.getdata()

    # render logobg, banner, logo
    banner = Image.new("RGB", (1700,300),(255,255,255))
    Image.Image.paste(banner, logobg, (0,-650)) # paste background logo directly
    datas = banner.getdata()
    logod = logo.getdata()
    newData = []
    for i in range(0,300):
        for j in range(0,1700):
            if i >= 25 and i < 275 and j >= 35 and j < 285:
                # paste avatar
                bg_a = 1 - avatar[(i-25)*250+(j-35)][3] / 255
                fg_a = avatar[(i-25)*250+(j-35)][3] / 255
                bg = datas[i*1700+j]
                fg = avatar[(i-25)*250+(j-35)]
                newData.append((int(bg[0]*bg_a+fg[0]*fg_a), int(bg[1]*bg_a+fg[1]*fg_a), int(bg[2]*bg_a+fg[2]*fg_a)))
            elif i >= 25 and i < 225 and j >= 1475 and j < 1675:
                # paste logo
                bg_a = 1 - logod[(i-25)*200+(j-1475)][3] / 255
                fg_a = logod[(i-25)*200+(j-1475)][3] / 255
                bg = datas[i*1700+j]
                fg = logod[(i-25)*200+(j-1475)]
                newData.append((int(bg[0]*bg_a+fg[0]*fg_a), int(bg[1]*bg_a+fg[1]*fg_a), int(bg[2]*bg_a+fg[2]*fg_a)))
            else:
                newData.append(datas[i*1700+j][:3])
    banner.putdata(newData)

    # draw text
    draw = ImageDraw.Draw(banner)
    # load font
    usH45 = ImageFont.truetype("./fonts/UniSansHeavy.ttf", 45)
    coH40 = ImageFont.truetype("./fonts/ConsolaBold.ttf", 40)
    # set color
    theme_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    # company name
    company_name_len = usH45.getsize(f"{company_name}")[0]
    draw.text((1700 - 25 - company_name_len, 245), f"{company_name}", fill=theme_color, font=usH45)

    name = form["name"]
    for _ in range(10):
        if name.startswith(" "):
            name = name[1:]
        else:
            break
    fontsize = 80
    offset = 0
    offsetp = 0
    namefont = ImageFont.truetype("./fonts/ConsolaBold.ttf", fontsize)
    namesize = namefont.getsize(f"{name}")[0]
    for _ in range(10):
        if namesize > 450:
            fontsize -= 10
            if offset <= 20:
                offset += 5
            else:
                offsetp += 5
            namefont = ImageFont.truetype("./fonts/ConsolaBold.ttf", fontsize)
            namesize = namefont.getsize(f"{name}")[0]
    draw.text((325, 50 + offset), f"{name}", fill=(0,0,0), font=namefont)
    # y = 50 ~ 70

    fontsize -= 10
    highest_role = form["highest_role"]
    for _ in range(10):
        if highest_role.startswith(" "):
            highest_role = highest_role[1:]
        else:
            break
    if fontsize >= 70:
        fontsize -= 10
    elif fontsize >= 60:
        fontsize -= 10
        offset -= 10
    else:
        offset -= 10
        offset += int(offsetp / 2)
    hrolefont = ImageFont.truetype("./fonts/Impact.ttf", fontsize)
    hrolesize = hrolefont.getsize(f"{highest_role}")[0]
    for _ in range(10):
        if hrolesize > 450:
            fontsize -= 10
            offset += 5
            hrolefont = ImageFont.truetype("./fonts/Impact.ttf", fontsize)
            hrolesize = hrolefont.getsize(f"{highest_role}")[0]
    draw.text((325, 125 + offset), f"{highest_role}", fill=theme_color, font=hrolefont)
    # y = 115 ~ 155

    since = form["since"]
    division = form["division"]
    distance = form["distance"]
    profit = form["profit"]
    sincefont = ImageFont.truetype("./fonts/Consola.ttf", 40)
    draw.text((325, 210), f"Since {since}", fill=(0,0,0), font=sincefont)
    # separate line
    draw.line((850, 25, 850, 275), fill=theme_color, width = 10)
    for _ in range(10):
        if division.startswith(" "):
            division = division[1:]
        else:
            break
    draw.text((900, 50), f"Division: {division}", fill=(0,0,0), font=coH40)
    draw.text((900, 110), f"Distance: {distance}", fill=(0,0,0), font=coH40)
    draw.text((900, 170), f"Income: {profit}", fill=(0,0,0), font=coH40)

    # output
    output = BytesIO()
    banner.save(output, "jpeg", optimize = True)
    open(f"/tmp/hub/banner/{company_abbr}_{discordid}.png","wb").write(output.getvalue())
    
    response = StreamingResponse(iter([output.getvalue()]), media_type="image/jpeg")
    return response