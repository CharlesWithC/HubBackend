# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

def point2rankroleid(app, point):
    """Returns Discord Snowflake of the rank of the point"""

    keys = list(app.rankrole.keys())
    if point < keys[0]:
        return -1
    if point >= keys[0] and (len(keys) == 1 or point < keys[1]):
        return app.rankrole[keys[0]]
    for i in range(1, len(keys)):
        if point >= keys[i-1] and point < keys[i]:
            return app.rankrole[keys[i-1]]
    if point >= keys[-1]:
        return app.rankrole[keys[-1]]

def point2rankname(app, point):
    """Returns name of the rank of the point"""

    keys = list(app.rankname.keys())
    if point < keys[0]:
        return -1
    if point >= keys[0] and (len(keys) == 1 or point < keys[1]):
        return app.rankname[keys[0]]
    for i in range(1, len(keys)):
        if point >= keys[i-1] and point < keys[i]:
            return app.rankname[keys[i-1]]
    if point >= keys[-1]:
        return app.rankname[keys[-1]]