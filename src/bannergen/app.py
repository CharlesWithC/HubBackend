# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from PIL import Image, ImageFont, ImageDraw
import numpy as np
import requests, os
from io import BytesIO
from datetime import datetime
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/banner")
async def banner(request: Request, response: Response):
    form = await request.form()
    vtc_abbr = form["vtc_abbr"]
    vtc_name = form["vtc_name"]
    vtc_logo_link = form["vtc_logo_link"]
    hex_color = form["hex_color"][-6:]

    logo = Image.new("RGBA", (400,400),(255,255,255))
    logobg = Image.new("RGB", (3400,3400),(255,255,255))

    if os.path.exists(f"/tmp/hub/logo/{vtc_abbr}.png"):
        logo = Image.open(f"/tmp/hub/logo/{vtc_abbr}.png").convert("RGBA")
        logobg = Image.open(f"/tmp/hub/logo/{vtc_abbr}_bg.png").convert("RGB")
    else:
        r = requests.get(vtc_logo_link, timeout = 10)
        if r.status_code == 200:
            vtc_logo = r.content
            vtc_logo = Image.open(BytesIO(vtc_logo)).convert("RGBA")

            logo = vtc_logo
            logobg = vtc_logo
            lnd = []
            lbnd = []
            datas = vtc_logo.getdata()
            for item in datas:
                if item[3] == 0:
                    lnd.append((255, 255, 255, 255))
                    lbnd.append((255, 255, 255, 255))
                else:
                    lnd.append((item[0], item[1], item[2], 255))
                    lbnd.append((int(0.85*255+0.15*item[0]), int(0.85*255+0.15*item[1]), int(0.85*255+0.15*item[2]), 255))
            logo.putdata(lnd)
            logo = logo.resize((400, 400), resample=Image.ANTIALIAS).convert("RGBA")
            logobg.putdata(lbnd)
            logobg = logobg.resize((3400, 3400), resample=Image.ANTIALIAS).convert("RGB")

            logo.save(f"/tmp/hub/logo/{vtc_abbr}.png")
            logobg.save(f"/tmp/hub/logo/{vtc_abbr}_bg.png")

    discordid = form["discordid"]
    avatar = form["avatar"]
    avatarid = avatar
    if os.path.exists(f"/tmp/hub/avatar/{discordid}_{avatar}.png"):
        avatar = Image.open(f"/tmp/hub/avatar/{discordid}_{avatar}.png")
        avatar = avatar.getdata()
    else:
        # pre-process avatar
        avatarurl = ""
        if avatar.startswith("a_"):
            avatarurl = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.gif"
        else:
            avatarurl = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.png"
        r = requests.get(avatarurl, timeout=3)
        if r.status_code == 200:
            avatar = Image.open(BytesIO(r.content)).resize((500, 500)).convert("RGB")
        else:
            avatar = logo.resize((500, 500), resample=Image.ANTIALIAS).convert("RGB")
        img = avatar
        height,width = img.size
        lum_img = Image.new('L', [height,width] , 0)
        draw = ImageDraw.Draw(lum_img)
        draw.pieslice([(0,0), (height,width)], 0, 360, fill = 255, outline = "white")
        img_arr = np.array(img)
        lum_img_arr = np.array(lum_img)
        final_img_arr = np.dstack((img_arr,lum_img_arr))
        avatar = Image.fromarray(final_img_arr).convert("RGBA")
        avatar.save(f"/tmp/hub/avatar/{discordid}_{avatarid}.png")
        avatar = avatar.getdata()

    # render logobg, banner, logo
    banner = Image.new("RGB", (3400,600),(255,255,255))
    Image.Image.paste(banner, logobg, (0,-1300))
    datas = banner.getdata()
    logod = logo.getdata()
    newData = []
    for i in range(0,600):
        for j in range(0,3400):
            if i >= 50 and i < 550 and j >= 70 and j < 570:
                if avatar[(i-50)*500+(j-70)][3] == 0:
                    newData.append(datas[i*3400+j][:3])
                else:
                    newData.append(avatar[(i-50)*500+(j-70)][:3])
            elif i >= 50 and i < 450 and j >= 2950 and j < 3350:
                if logod[(i-50)*400+(j-2950)][3] == 0:
                    newData.append(datas[i*3400+j][:3])
                else:
                    newData.append(logod[(i-50)*400+(j-2950)][:3])
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
    vtccolor = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    # vtc name
    vtcnamelen = usH90.getsize(f"{vtc_name}")[0]
    draw.text((3400 - 50 - vtcnamelen, 490), f"{vtc_name}", fill=vtccolor, font=usH90)

    name = form["name"]
    while name.startswith(" "):
        name = name[1:]
    fontsize = 160
    offset = 0
    namefont = ImageFont.truetype("./fonts/ConsolaBold.ttf", fontsize)
    namesize = namefont.getsize(f"{name}")[0]
    for _ in range(10):
        if namesize > 900:
            fontsize -= 10
            offset += 10
            namefont = ImageFont.truetype("./fonts/ConsolaBold.ttf", fontsize)
            namesize = namefont.getsize(f"{name}")[0]
    draw.text((650, 100 + offset), f"{name}", fill=(0,0,0), font=namefont)

    highest_role = form["highest_role"]
    while highest_role.startswith(" "):
        highest_role = highest_role[1:]
    if fontsize >= 120:
        fontsize -= 40
    else:
        offset -= 40
    hrolefont = ImageFont.truetype("./fonts/Impact.ttf", fontsize)
    hrolesize = hrolefont.getsize(f"{highest_role}")[0]
    for _ in range(10):
        if hrolesize > 900:
            fontsize -= 10
            offset += 10
            hrolefont = ImageFont.truetype("./fonts/Impact.ttf", fontsize)
            hrolesize = hrolefont.getsize(f"{highest_role}")[0]
    draw.text((650, 240 + offset), f"{highest_role}", fill=vtccolor, font=hrolefont)

    since = form["since"]
    division = form["division"]
    distance = form["distance"]
    profit = form["profit"]
    sincefont = ImageFont.truetype("./fonts/Consola.ttf", 80)
    draw.text((650, 420), f"Since {since}", fill=(0,0,0), font=sincefont)
    # separate line
    draw.line((1700, 50, 1700, 550), fill=vtccolor, width = 20)
    while division.startswith(" "):
        division = division[1:]
    draw.text((1800, 100), f"Division: {division}", fill=(0,0,0), font=coH80)
    draw.text((1800, 220), f"Distance: {distance}", fill=(0,0,0), font=coH80)
    draw.text((1800, 340), f"Income: {profit}", fill=(0,0,0), font=coH80)

    # output
    output = BytesIO()
    banner.save(output, "jpeg")
    
    response = StreamingResponse(iter([output.getvalue()]), media_type="image/jpeg")
    return response