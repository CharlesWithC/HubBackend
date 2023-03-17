from static import RANKROLE, RANKNAME

def point2rankroleid(point):
    """Returns Discord Snowflake of the rank of the point"""

    keys = list(RANKROLE.keys())
    if point < keys[0]:
        return -1
    if point >= keys[0] and (len(keys) == 1 or point < keys[1]):
        return RANKROLE[keys[0]]
    for i in range(1, len(keys)):
        if point >= keys[i-1] and point < keys[i]:
            return RANKROLE[keys[i-1]]
    if point >= keys[-1]:
        return RANKROLE[keys[-1]]

def point2rankname(point):
    """Returns name of the rank of the point"""

    keys = list(RANKNAME.keys())
    if point < keys[0]:
        return -1
    if point >= keys[0] and (len(keys) == 1 or point < keys[1]):
        return RANKNAME[keys[0]]
    for i in range(1, len(keys)):
        if point >= keys[i-1] and point < keys[i]:
            return RANKNAME[keys[i-1]]
    if point >= keys[-1]:
        return RANKNAME[keys[-1]]