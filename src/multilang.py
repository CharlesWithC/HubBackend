# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import Request
from typing import Optional
import os, json

from app import config

def get_lang(request: Request):
    lang = request.headers.get('Accept-Language', 'en')
    lang = lang.split(',')[0]
    lang = lang.split(';')[0]
    lang = lang.split('-')[0]
    return lang

def translate(request: Request, key: str, var: Optional[dict] = {}, force_en: Optional[bool] = False):
    lang = get_lang(request)
    langdir = config.language_dir
    if not os.path.exists(langdir + "/" + lang + ".json"): # no translation for language
        lang = "en" 
    if force_en:
        lang = "en"
    langdata = json.loads(open(langdir + "/" + lang + ".json", "r").read())
    if key in langdata:
        ret = langdata[key]
        for vkey in var.keys():
            ret = ret.replace("{" + vkey + "}", str(var[vkey]))
        return ret
    else: # no translation for key
        if lang != "en": # try english
            langdata = json.loads(open(langdir + "/en.json", "r").read())
            if key in langdata:
                ret = langdata[key]
                for vkey in var.keys():
                    ret = ret.replace("{" + vkey + "}", str(var[vkey]))
                return ret
            else: # invalid key
                return ""
        else: # invalid key
            return ""

def tr(request: Request, key: str, var: Optional[dict] = {}, force_en: Optional[bool] = False): # abbreviation of translate
    return translate(request, key, var, force_en)