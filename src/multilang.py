# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import os
from typing import Optional

from fastapi import Request

from static import EN_STRINGTABLE

import inspect

abspath = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename))

LANGUAGES = os.listdir(os.path.join(abspath, "languages/"))
LANGUAGES = [x.split(".")[0].lower() for x in LANGUAGES]
LANG_DATAS = {}
for LANGUAGE in LANGUAGES:
    try:
        LANG_DATAS[LANGUAGE] = json.loads(open(os.path.join(abspath, f"languages/{LANGUAGE}.json"),"r").read())
    except:
        pass
LANGUAGES = sorted(list(LANG_DATAS.keys())) # must be valid language file

def get_lang(request: Request):
    if request is None:
        return request.app.config.language
    lang = request.headers.get('Accept-Language', 'en').lower()
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

def spl(key: str, var: Optional[dict] = {}):
    return {"key": key, "var": var}

def hspl(request: Request, data, force_lang: Optional[str] = ""):
    if type(data) == str:
        return data
    elif type(data) == dict:
        return translate(request, data["key"], data["var"], force_lang)

def company_translate(request: Request, key: str, var: Optional[dict] = {}, force_lang: Optional[str] = ""):
    lang = request.app.config.language if force_lang == "" else force_lang
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

def ctr(request: Request, key: str, var: Optional[dict] = {}, force_lang: Optional[str] = ""):
    return company_translate(request, key, var, force_lang)