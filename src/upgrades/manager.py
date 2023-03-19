VERSION_CHAIN = ["v2_0_0", "v2_0_1", "v2_1_0", "v2_1_1", "v2_1_2", "v2_1_3", "v2_1_4", "v2_1_5", "v2_1_6", "v2_2_0", "v2_2_1", "v2_2_2", "v2_2_3"]

UPGRADEABLE_VERSION = ["v2_1_0", "v2_1_1", "v2_1_5"]

UPGRADER = {}

import upgrades.v2_1_0
UPGRADER["v2_1_0"] = upgrades.v2_1_0

import upgrades.v2_1_1
UPGRADER["v2_1_1"] = upgrades.v2_1_1

import upgrades.v2_1_5
UPGRADER["v2_1_5"] = upgrades.v2_1_5

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
        delete_module(f"upgrades.{v}")
    delete_module("upgrades.manager")