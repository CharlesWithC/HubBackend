# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import upgrades.v2_1_0
import upgrades.v2_1_1
import upgrades.v2_1_5
import upgrades.v2_2_4
import upgrades.v2_3_1
import upgrades.v2_5_8
import upgrades.v2_6_0
import upgrades.v2_6_2
import upgrades.v2_7_2
import upgrades.v2_7_3
import upgrades.v2_8_2
import upgrades.v2_8_9
import upgrades.v2_9_1
import upgrades.v2_9_2
import upgrades.v2_10_2

VERSION_CHAIN = ["2_0_0", "2_0_1", "2_1_0", "2_1_1", "2_1_2", "2_1_3", "2_1_4", "2_1_5", "2_1_6", "2_2_0", "2_2_1", "2_2_2", "2_2_3", "2_2_4", "2_3_0", "2_3_1", "2_4_0", "2_4_1", "2_4_2", "2_4_3", "2_4_4", "2_5_0", "2_5_1", "2_5_2", "2_5_3", "2_5_4", "2_5_5", "2_5_6", "2_5_7", "2_5_8", "2_5_9", "2_5_10", "2_5_11", "2_6_0", "2_6_1", "2_6_2", "2_6_3", "2_7_0", "2_7_1", "2_7_2", "2_7_3", "2_7_4", "2_7_5", "2_7_6", "2_7_7", "2_7_8", "2_7_9", "2_7_10", "2_7_11", "2_7_12", "2_7_13", "2_7_14", "2_7_15", "2_8_0", "2_8_1", "2_8_2", "2_8_3", "2_8_4", "2_8_5", "2_8_6", "2_8_7", "2_8_8", "2_8_9", "2_8_10", "2_9_0", "2_9_1", "2_9_2", "2_9_3", "2_9_4", "2_9_5", "2_10_0", "2_10_1", "2_10_2", "2_10_3"]

UPGRADER = {}
UPGRADER["2_1_0"] = upgrades.v2_1_0
UPGRADER["2_1_1"] = upgrades.v2_1_1
UPGRADER["2_1_5"] = upgrades.v2_1_5
UPGRADER["2_2_4"] = upgrades.v2_2_4
UPGRADER["2_3_1"] = upgrades.v2_3_1
UPGRADER["2_5_8"] = upgrades.v2_5_8
UPGRADER["2_6_0"] = upgrades.v2_6_0
UPGRADER["2_6_2"] = upgrades.v2_6_2
UPGRADER["2_7_2"] = upgrades.v2_7_2
UPGRADER["2_7_3"] = upgrades.v2_7_3
UPGRADER["2_8_2"] = upgrades.v2_8_2
UPGRADER["2_8_9"] = upgrades.v2_8_9
UPGRADER["2_9_1"] = upgrades.v2_9_1
UPGRADER["2_9_2"] = upgrades.v2_9_2
UPGRADER["2_10_2"] = upgrades.v2_10_2

def delete_module(modname):
    from sys import modules
    try:
        modules[modname]
    except KeyError:
        raise ValueError(modname)
    del modules[modname]
    for mod in modules.values():
        try:
            delattr(mod, modname)
        except AttributeError:
            pass

def unload():
    for v in UPGRADER:
        delete_module(f"upgrades.v{v}")
    delete_module("upgrades.manager")
