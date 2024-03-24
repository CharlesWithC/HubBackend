# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

def point2rank(app, rank_type_id, point):
    if rank_type_id == "default":
        for rank_type in app.config.rank_types:
            if rank_type["default"]:
                rank_type_id = rank_type["id"]

    ranks = app.ranktypes[rank_type_id]
    keys = list(ranks.keys())
    if point < keys[0]:
        return None
    if point >= keys[0] and (len(keys) == 1 or point < keys[1]):
        return ranks[keys[0]]
    for i in range(1, len(keys)):
        if point >= keys[i-1] and point < keys[i]:
            return ranks[keys[i-1]]
    if point >= keys[-1]:
        return ranks[keys[-1]]
