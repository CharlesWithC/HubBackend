# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import os
from typing import Optional

from fastapi import Request

from app import app
from static import EN_STRINGTABLE

LANGUAGES = os.listdir(app.config.language_dir)
LANGUAGES = [x.split(".")[0] for x in LANGUAGES]
LANG_DATAS = {}
for lang in LANGUAGES:
    try:
        LANG_DATAS[lang] = json.loads(open(f"{app.config.language_dir}/{lang}.json","r").read())
    except:
        pass
LANGUAGES = LANG_DATAS.keys() # must be valid language file

def get_lang(request: Request):
    if request is None:
        return app.config.language
    lang = request.headers.get('Accept-Language', 'en')
    lang = lang.split(',')[0]
    lang = lang.split(';')[0]

    # try aa-bb
    if lang not in LANGUAGES:
        # aa-bb (e.g. en-us) exists
        return lang
    
    # aa-bb doesn't exist, returns aa
    lang = lang.split('-')[0]
    return lang

def translate(request: Request, key: str, var: Optional[dict] = {}, force_lang: Optional[str] = ""):
    lang = get_lang(request) if force_lang == "" else force_lang
    if lang not in LANGUAGES:
        lang = "en" 

    LANG_DATA = EN_STRINGTABLE
    if lang != "en":
        LANG_DATA = LANG_DATAS[lang]

    if key in LANG_DATA:
        ret = LANG_DATA[key]
        for vkey in var.keys():
            ret = ret.replace("{" + vkey + "}", str(var[vkey]))
        return ret
    else: # no translation for key
        if lang != "en": # try english
            LANG_DATA = EN_STRINGTABLE
            if key in LANG_DATA:
                ret = LANG_DATA[key]
                for vkey in var.keys():
                    ret = ret.replace("{" + vkey + "}", str(var[vkey]))
                return ret
            else: # invalid key
                return key
        else: # invalid key
            return key

def tr(request: Request, key: str, var: Optional[dict] = {}, force_lang: Optional[str] = ""): # abbreviation of translate
    return translate(request, key, var, force_lang)

def company_translate(key: str, var: Optional[dict] = {}, force_lang: Optional[str] = ""):
    lang = app.config.language if force_lang == "" else force_lang
    if lang not in LANGUAGES:
        lang = "en" 

    LANG_DATA = EN_STRINGTABLE
    if lang != "en":
        LANG_DATA = LANG_DATAS[lang]

    if key in LANG_DATA:
        ret = LANG_DATA[key]
        for vkey in var.keys():
            ret = ret.replace("{" + vkey + "}", str(var[vkey]))
        return ret
    else: # no translation for key
        if lang != "en": # try english
            LANG_DATA = EN_STRINGTABLE
            if key in LANG_DATA:
                ret = LANG_DATA[key]
                for vkey in var.keys():
                    ret = ret.replace("{" + vkey + "}", str(var[vkey]))
                return ret
            else: # invalid key
                return key
        else: # invalid key
            return key

def ctr(key: str, var: Optional[dict] = {}, force_lang: Optional[str] = ""):
    return company_translate(key, var, force_lang)