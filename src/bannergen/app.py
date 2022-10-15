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

    logo = Image.new("RGBA", (400,400),(255,255,255))
    logobg = Image.new("RGB", (3400,3400),(255,255,255))

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
                logo = logo.resize((400, 400), resample=Image.ANTIALIAS).convert("RGBA")
                logobg.putdata(lbnd)
                logobg = logobg.resize((3400, 3400), resample=Image.ANTIALIAS).convert("RGB")

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
                    avatar = Image.open(BytesIO(r.content)).resize((500, 500)).convert("RGBA")
                except:
                    avatar = logo.resize((500, 500)).convert("RGBA")
            else:
                avatar = logo.resize((500, 500)).convert("RGBA")
            def dist(a,b,c,d):
                return (c-a)*(c-a)+(b-d)*(b-d)
            data = avatar.getdata()
            newData = []
            for i in range(0,500):
                for j in range(0,500):
                    if dist(i,j,250,250) > 250*250:
                        newData.append((255,255,255,0))
                    else:
                        newData.append(data[i*500+j])
            avatar.putdata(newData)
            avatar.save(f"/tmp/hub/avatar/{discordid}_{avatarid}.png", optimize = True)
        except:
            pass
    avatar = avatar.getdata()

    # render logobg, banner, logo
    banner = Image.new("RGB", (3400,600),(255,255,255))
    Image.Image.paste(banner, logobg, (0,-1300)) # paste background logo directly
    datas = banner.getdata()
    logod = logo.getdata()
    newData = []
    for i in range(0,600):
        for j in range(0,3400):
            if i >= 50 and i < 550 and j >= 70 and j < 570:
                # paste avatar
                bg_a = 1 - avatar[(i-50)*500+(j-70)][3] / 255
                fg_a = avatar[(i-50)*500+(j-70)][3] / 255
                bg = datas[i*3400+j]
                fg = avatar[(i-50)*500+(j-70)]
                newData.append((int(bg[0]*bg_a+fg[0]*fg_a), int(bg[1]*bg_a+fg[1]*fg_a), int(bg[2]*bg_a+fg[2]*fg_a)))
            elif i >= 50 and i < 450 and j >= 2950 and j < 3350:
                # paste logo
                bg_a = 1 - logod[(i-50)*400+(j-2950)][3] / 255
                fg_a = logod[(i-50)*400+(j-2950)][3] / 255
                bg = datas[i*3400+j]
                fg = logod[(i-50)*400+(j-2950)]
                newData.append((int(bg[0]*bg_a+fg[0]*fg_a), int(bg[1]*bg_a+fg[1]*fg_a), int(bg[2]*bg_a+fg[2]*fg_a)))
            else:
                newData.append(datas[i*3400+j][:3])
    banner.putdata(newData)

    # draw text
    draw = ImageDraw.Draw(banner)
    # load font
    usH90 = ImageFont.truetype("./fonts/UniSansHeavy.ttf", 90)
    coH80 = ImageFont.truetype("./fonts/ConsolaBold.ttf", 80)
    co20 = ImageFont.truetype("./fonts/Consola.ttf", 20)
    # set color
    theme_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    # company name
    company_name_len = usH90.getsize(f"{company_name}")[0]
    draw.text((3400 - 50 - company_name_len, 490), f"{company_name}", fill=theme_color, font=usH90)

    name = form["name"]
    for _ in range(10):
        if name.startswith(" "):
            name = name[1:]
        else:
            break
    fontsize = 160
    offset = 0
    offsetp = 0
    namefont = ImageFont.truetype("./fonts/ConsolaBold.ttf", fontsize)
    namesize = namefont.getsize(f"{name}")[0]
    for _ in range(10):
        if namesize > 900:
            fontsize -= 10
            if offset <= 40:
                offset += 10
            else:
                offsetp += 10
            namefont = ImageFont.truetype("./fonts/ConsolaBold.ttf", fontsize)
            namesize = namefont.getsize(f"{name}")[0]
    draw.text((650, 100 + offset), f"{name}", fill=(0,0,0), font=namefont)
    # y = 100 ~ 140

    highest_role = form["highest_role"]
    for _ in range(10):
        if highest_role.startswith(" "):
            highest_role = highest_role[1:]
        else:
            break
    if fontsize >= 140:
        fontsize -= 40
    elif fontsize >= 120:
        fontsize -= 20
        offset -= 20
    else:
        offset -= 40
        offset += int(offsetp / 2)
    hrolefont = ImageFont.truetype("./fonts/Impact.ttf", fontsize)
    hrolesize = hrolefont.getsize(f"{highest_role}")[0]
    for _ in range(10):
        if hrolesize > 900:
            fontsize -= 10
            offset += 10
            hrolefont = ImageFont.truetype("./fonts/Impact.ttf", fontsize)
            hrolesize = hrolefont.getsize(f"{highest_role}")[0]
    draw.text((650, 240 + offset), f"{highest_role}", fill=theme_color, font=hrolefont)
    # y = 240 ~ 280

    since = form["since"]
    division = form["division"]
    distance = form["distance"]
    profit = form["profit"]
    sincefont = ImageFont.truetype("./fonts/Consola.ttf", 80)
    draw.text((650, 420), f"Since {since}", fill=(0,0,0), font=sincefont)
    # separate line
    draw.line((1700, 50, 1700, 550), fill=theme_color, width = 20)
    for _ in range(10):
        if division.startswith(" "):
            division = division[1:]
        else:
            break
    draw.text((1800, 100), f"Division: {division}", fill=(0,0,0), font=coH80)
    draw.text((1800, 220), f"Distance: {distance}", fill=(0,0,0), font=coH80)
    draw.text((1800, 340), f"Income: {profit}", fill=(0,0,0), font=coH80)

    # output
    output = BytesIO()
    banner.save(output, "jpeg", optimize = True)
    open(f"/tmp/hub/banner/{company_abbr}_{discordid}.png","wb").write(output.getvalue())
    
    response = StreamingResponse(iter([output.getvalue()]), media_type="image/jpeg")
    return response