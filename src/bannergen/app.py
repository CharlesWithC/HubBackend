# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from PIL import Image, ImageFont, ImageDraw
import requests, os, time, string, unicodedata
from io import BytesIO
from datetime import datetime
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from fontTools.ttLib import TTFont
from fontTools.unicode import Unicode

app = FastAPI()

tt_namefont = TTFont("./fonts/ConsolaBold.ttf")
def has_glyph(glyph):
    for table in tt_namefont['cmap'].tables:
        if ord(glyph) in table.cmap.keys():
            return True
    return False

# Due to the nature of Consola font family has same width for all characters
# We can preload its wsize to prevent using .getsize() which is slow
# NOTE that non-printable characters from Sans Serif will still need .getsize()
consola_bold_font_wsize = []
for i in range(81):
    font = ImageFont.truetype("./fonts/ConsolaBold.ttf", i)
    wsize = font.getlength("a")
    consola_bold_font_wsize.append(wsize)

@app.post("/banner")
async def banner(request: Request, response: Response):
    form = await request.form()
    company_abbr = form["company_abbr"]
    company_name = form["company_name"]
    company_name = unicodedata.normalize('NFKC', company_name)
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

    # if os.path.exists(f"/tmp/hub/banner/{company_abbr}_{discordid}.png"):
    #     if time.time() - os.path.getmtime(f"/tmp/hub/banner/{company_abbr}_{discordid}.png") <= 3600:
    #         response = StreamingResponse(iter([open(f"/tmp/hub/banner/{company_abbr}_{discordid}.png","rb").read()]), media_type="image/jpeg")
    #         return response

    logo = Image.new("RGBA", (200,200),(255,255,255))
    banner = Image.new("RGB", (1700,300),(255,255,255))

    if os.path.exists(f"/tmp/hub/logo/{company_abbr}.png") and os.path.exists(f"/tmp/hub/template/{company_abbr}.png"):
        logo = Image.open(f"/tmp/hub/logo/{company_abbr}.png")
        banner = Image.open(f"/tmp/hub/template/{company_abbr}.png")
    else:
        r = requests.get(logo_url, timeout = 3)
        if r.status_code == 200:
            logo = r.content
            try: # in case image is invalid
                logo = Image.open(BytesIO(logo)).convert("RGBA")
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
                logo = logo.resize((200, 200), resample=Image.ANTIALIAS).convert("RGBA")
                logo.save(f"/tmp/hub/logo/{company_abbr}.png", optimize = True)
                logo_datas = logo.getdata()
                
                logo_large.putdata(logo_large_datas)
                logo_large = logo_large.resize((1700, 1700), resample=Image.ANTIALIAS).convert("RGB")

                # render logo
                banner = logo_large.crop((0, 700, 1700, 1000))
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
                
                # draw company name
                draw = ImageDraw.Draw(banner)
                usH45 = ImageFont.truetype("./fonts/UniSansHeavy.ttf", 45)
                theme_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                company_name_len = usH45.getlength(f"{company_name}")
                draw.text((1700 - 25 - company_name_len, 245), f"{company_name}", fill=theme_color, font=usH45)

                banner.save(f"/tmp/hub/template/{company_abbr}.png", optimize = True)                

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

    # draw text
    draw = ImageDraw.Draw(banner)
    theme_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # draw name
    name = form["name"]
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

    l = 0
    r = 80
    fontsize = 80
    while r - l > 1:
        fontsize = (l + r) // 2
        if all_printable:
            namew = consola_bold_font_wsize[fontsize] * len(name)
        else:
            namefont = ImageFont.truetype("./fonts/ConsolaBold.ttf", fontsize)
            namew = namefont.getlength(f"{name}")
        if namew > 450:
            r = fontsize - 1
        else:
            l = fontsize + 1
    namefont = ImageFont.truetype("./fonts/ConsolaBold.ttf", fontsize)
    namebb = namefont.getbbox(f"{name}")
    nameh = namebb[3] - namebb[1]
    offset = min(fontsize * 0.05, 20)
    draw.text((325, 50 + offset - namebb[1]), name, fill=(0,0,0), font=namefont)
    # y = 50 ~ 70

    fontsize -= 10
    highest_role = form["highest_role"]
    highest_role = unicodedata.normalize('NFKC', highest_role).lstrip(" ")
    hrolefont = ImageFont.truetype("./fonts/Impact.ttf", fontsize)
    hrolew = hrolefont.getlength(f"{highest_role}")
    for _ in range(100):
        if hrolew > 450:
            fontsize -= 1
            hrolefont = ImageFont.truetype("./fonts/Impact.ttf", fontsize)
            hrolew = hrolefont.getlength(f"{highest_role}")
    hrolebb = hrolefont.getbbox(f"{highest_role}")
    hroleh = hrolebb[3] - hrolebb[1]

    nameb = 50 + offset + nameh
    sincet = 210
    draw.text((325, (sincet + nameb - hroleh) / 2 - hrolebb[1]), f"{highest_role}", fill=theme_color, font=hrolefont)
    # y = 115 ~ 155

    since = form["since"]
    division = form["division"]
    division = unicodedata.normalize('NFKC', division).lstrip(" ")
    distance = form["distance"]
    profit = form["profit"]
    sincefont = ImageFont.truetype("./fonts/Consola.ttf", 40)
    draw.text((325, 220), f"Since {since}", fill=(0,0,0), font=sincefont)

    # separate line
    coH40 = ImageFont.truetype("./fonts/ConsolaBold.ttf", 40)
    draw.line((850, 25, 850, 275), fill=theme_color, width = 10)
    divisionw = coH40.getlength(f"Division: {division}")
    if divisionw > 550:
        division += "..."
    while divisionw > 550:
        division = division[:-4] + "..."
        divisionw = coH40.getlength(f"Division: {division}")
    draw.text((900, 50), f"Division: {division}", fill=(0,0,0), font=coH40)
    draw.text((900, 110), f"Distance: {distance}", fill=(0,0,0), font=coH40)
    draw.text((900, 170), f"Income: {profit}", fill=(0,0,0), font=coH40)

    # output
    output = BytesIO()
    banner.save(output, "jpeg", optimize = True)
    open(f"/tmp/hub/banner/{company_abbr}_{discordid}.png","wb").write(output.getvalue())
    
    response = StreamingResponse(iter([output.getvalue()]), media_type="image/jpeg")
    return response