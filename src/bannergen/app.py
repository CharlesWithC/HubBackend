# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from PIL import Image, ImageFont, ImageDraw
import requests, os, time, string, unicodedata
from io import BytesIO
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

app = FastAPI()

# ConsoleBold.ttf
supported_glyph_ord_range = [0, (8, 9), 13, 29, (32, 126), (128, 887), (890, 895), (900, 906), 908, (910, 929), (931, 1327), (1329, 1366), (1369, 1375), (1377, 1415), (1417, 1418), (1421, 1423), (1425, 1479), (1488, 1514), (1520, 1524), (1536, 1564), (1566, 1651), (1653, 1791), (1872, 1919), 1923, (2208, 2228), (2230, 2237), (2260, 2303), (2546, 2547), 2801, 3065, (3585, 3642), (3647, 3675), (4256, 4293), 4295, 4301, (4304, 4351), 6107, (7424, 7626), (7678, 7957), (7960, 7965), (7968, 8005), (8008, 8013), (8016, 8023), 8025, 8027, 8029, (8031, 8061), (8064, 8116), (8118, 8132), (8134, 8147), (8150, 8155), (8157, 8175), (8178, 8180), (8182, 8190), (8192, 8292), (8294, 8305), (8308, 8334), (8336, 8348), (8352, 8383), 8413, 8419, 8432, 8453, 8467, (8470, 8471), 8482, 8486, 8494, (8498, 8499), (8525, 8526), (8528, 8587), (8592, 8597), 8616, 8706, 8710, 8719, (8721, 8722), 8725, (8729, 8730), (8734, 8735), 8745, 8747, 8776, (8800, 8801), (8804, 8805), 8962, 8976, (8992, 8993), (9312, 9331), (9450, 9460), (9471, 9472), 9474, 9484, 9488, 9492, 9496, 9500, 9508, 9516, 9524, 9532, (9552, 9580), 9600, 9604, 9608, 9612, (9616, 9619), (9632, 9633), (9642, 9644), 9650, 9652, 9656, 9658, 9660, 9662, 9666, 9668, (9674, 9676), 9679, (9688, 9689), 9702, (9786, 9788), 9792, 9794, 9824, 9827, (9829, 9830), (9834, 9835), 9839, 10038, (10102, 10111), (11360, 11391), (11520, 11557), 11559, 11565, (11744, 11775), 11799, (42560, 42655), (42775, 42925), (42928, 42935), (42999, 43007), (43824, 43877), (64256, 64262), (64275, 64279), (64285, 64310), (64312, 64316), 64318, (64320, 64321), (64323, 64324), (64326, 64335), 64337, 64340, 64344, 64348, 64352, 64356, 64360, (64364, 64365), (64368, 64369), (64371, 64372), (64375, 64376), (64379, 64380), (64383, 64384), 64395, 64397, 64400, 64404, 64408, 64412, (64421, 64422), (64424, 64425), 64427, 64431, (64433, 64449), 64469, 64485, 64488, 64490, 64492, 64494, 64496, 64498, 64500, 64502, (64504, 64505), 64507, (64509, 64510), (64606, 64611), (64754, 64756), (64828, 64831), 65010, 65012, (65018, 65021), (65056, 65059), (65136, 65140), (65142, 65151), 65154, 65156, 65160, (65162, 65163), 65166, 65169, 65172, (65175, 65176), (65179, 65180), (65182, 65183), (65186, 65187), (65190, 65191), 65198, 65200, 65203, 65207, 65211, 65215, (65226, 65228), (65230, 65232), (65235, 65236), (65239, 65240), 65243, (65246, 65248), 65251, 65255, 65258, 65264, (65266, 65276), 65279, (65532, 65533)]
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

    try:
        rgbcolor = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except:
        hex_color = "2fc1f7"
    
    l = os.listdir(f"/tmp/hub/banner")
    for ll in l:
        if time.time() - os.path.getmtime(f"/tmp/hub/banner/{ll}") > 7200:
            os.remove(f"/tmp/hub/banner/{ll}")

    if os.path.exists(f"/tmp/hub/banner/{company_abbr}_{discordid}.png"):
        if time.time() - os.path.getmtime(f"/tmp/hub/banner/{company_abbr}_{discordid}.png") <= 3600:
            response = StreamingResponse(iter([open(f"/tmp/hub/banner/{company_abbr}_{discordid}.png","rb").read()]), media_type="image/jpeg")
            return response

    logo = Image.new("RGBA", (200,200),(255,255,255))
    banner = Image.new("RGB", (1700,300),(255,255,255))

    if os.path.exists(f"/tmp/hub/logo/{company_abbr}.png") and os.path.exists(f"/tmp/hub/template/{company_abbr}.png"):
        logo = Image.open(f"/tmp/hub/logo/{company_abbr}.png")
        banner = Image.open(f"/tmp/hub/template/{company_abbr}.png")
    else:
        try:
            r = requests.get(logo_url, timeout = 5)

            if r.status_code == 200:
                logo = r.content
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

        except:
            pass

        # draw company name
        draw = ImageDraw.Draw(banner)
        usH45 = ImageFont.truetype("./fonts/UniSansHeavy.ttf", 45)
        theme_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        company_name_len = usH45.getlength(f"{company_name}")
        draw.text((1700 - 25 - company_name_len, 245), f"{company_name}", fill=theme_color, font=usH45)

        banner.save(f"/tmp/hub/template/{company_abbr}.png", optimize = True)
    
    avatar = form["avatar"]
    avatarid = avatar

    l = os.listdir(f"/tmp/hub/avatar")
    for ll in l:
        ldiscordid = ll.split("_")[0]
        lavatarid = "_".join(ll.split("_")[1:]).split(".")[0]
        if ldiscordid == discordid and lavatarid != avatarid:
            # user changed avatar
            os.remove(f"/tmp/hub/avatar/{ll}")
            continue
        if ldiscordid == discordid and lavatarid == avatarid:
            # user didn't change avatar, and user is active, preserve avatar longer
            mtime = os.path.getmtime(f"/tmp/hub/avatar/{ll}")
            os.utime(f"/tmp/hub/avatar/{ll}", (time.time(), mtime))
        if time.time() - os.path.getatime(f"/tmp/hub/avatar/{ll}") > 86400 * 7:
            os.remove(f"/tmp/hub/avatar/{ll}")
            continue

    if os.path.exists(f"/tmp/hub/avatar/{discordid}_{avatar}.png"):
        avatar = Image.open(f"/tmp/hub/avatar/{discordid}_{avatar}.png")
    else:
        if str(avatar) == "None":
            avatar = logo.resize((250, 250)).convert("RGBA")
        else:
            # pre-process avatar
            avatarurl = ""
            if avatar.startswith("a_"):
                avatarurl = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.gif"
            else:
                avatarurl = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.png"
            try: # in case image is invalid
                r = requests.get(avatarurl, timeout = 5)
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