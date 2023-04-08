VERSION_CHAIN = ["2_0_0", "2_0_1", "2_1_0", "2_1_1", "2_1_2", "2_1_3", "2_1_4", "2_1_5", "2_1_6", "2_2_0", "2_2_1", "2_2_2", "2_2_3", "2_2_4", "2_3_0", "2_3_1", "2_4_0", "2_4_1", "2_4_2", "2_4_3", "2_4_4", "2_5_0", "2_5_1", "2_5_2"]

UPGRADEABLE_VERSION = ["2_1_0", "2_1_1", "2_1_5", "2_2_4", "2_3_1"]

UPGRADER = {}

import upgrades.v2_1_0
UPGRADER["2_1_0"] = upgrades.v2_1_0

import upgrades.v2_1_1
UPGRADER["2_1_1"] = upgrades.v2_1_1

import upgrades.v2_1_5
UPGRADER["2_1_5"] = upgrades.v2_1_5

import upgrades.v2_2_4
UPGRADER["2_2_4"] = upgrades.v2_2_4

import upgrades.v2_3_1
UPGRADER["2_3_1"] = upgrades.v2_3_1

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