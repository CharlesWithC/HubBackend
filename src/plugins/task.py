# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# The task plugin.
# Core principle: Create/Assign tasks for members to complete.
# Side principle: Self-assign tasks as reminders.
#                 Bonus points when tasks are completed.

# Task Object
# title / description / creator / priority / bonus / due-date / remind-at
# recurring (every X seconds, update due date when reached)
# assigned-to-roles / assigned-to-users / self-assigned
# mark-completed / confirm-completed

# Notes

# When task is assigned to roles, all users with the roles are considered a GROUP.
# When any member of the GROUP completes the task, the creator receives a notification.
# The creator may then confirm the completion, and provide bonus points (to all members of the group).
# (Only one member is needed to mark as complete)

# When task is assigned to users, each user receives an individual task.
# When any user compeltes the task, the creator receives a notification.
# The creator may then confirm the completion, and provide bonus points (to the specific user).
# (Each user has to mark their own completion status)

# Bonus point goes to the traditional bonus system. We do not have a task-specific system for that.

# We also need Discord embed templates in config and task notification type added.
# Task will run its own notification handler but we'll use the centralized notification manager.

# Endpoints
# POST /tasks
# GET /tasks/list
# GET /tasks/{taskid}
# PATCH /tasks/{taskid}
# DELETE /tasks/{taskid}
# PUT /tasks/{taskid}/complete (self-put)
# DELETE /tasks/{taskid}/complete (self-put)
# PATCH /tasks/{taskid}/status (creator-patch)

# Background tasks
# Notification on task create
# Reminder on remind-at
# Create new task and set recurring = -recurring for old recurring task
# (When a recurring task reaches due date, create a new task with updated due date,
# and set recurring = -recurring to disable the old task)


import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_task_list(request: Request, response: Response, authorization: str = Header(None),\
                        page: Optional[int] = 1, page_size: Optional[int] = 10, \
                        order_by: Optional[str] = "priority", order: Optional[str] = "asc", \
                        title: Optional[str] = "", created_by: Optional[int] = None, \
                        mark_completed: Optional[bool] = False, confirm_completed: Optional[bool] = None, \
                        after_taskid: Optional[int] = None, is_recurring: Optional[bool] = None, \
                        created_before: Optional[int] = None, created_after: Optional[int] = None, \
                        due_before: Optional[int] = None, due_after: Optional[int] = None, \
                        min_priority: Optional[int] = None, max_priority: Optional[int] = None, \
                        min_bonus: Optional[int] = None, max_bonus: Optional[int] = None, \
                        assign_mode: Optional[int] = None, assign_to_userid: Optional[int] = None,\
                        assign_to_roleid: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /tasks/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    limit = ""
    if title != "":
        title = convertQuotation(title).lower()
        limit += f"AND LOWER(title) LIKE '%{title}%' "
    if created_by is not None:
        limit += f"AND userid = {created_by} "
    if mark_completed is not None:
        limit += f"AND mark_completed = {int(mark_completed)} "
    if confirm_completed is not None:
        limit += f"AND confirm_completed = {int(confirm_completed)} "
    if is_recurring is not None:
        if is_recurring:
            limit += "AND recurring != 0 "
        else:
            limit += "AND recurring = 0 "
    if created_before is not None:
        limit += f"AND create_timestamp <= {created_before} "
    if created_after is not None:
        limit += f"AND create_timestamp >= {created_after} "
    if due_before is not None:
        limit += f"AND due_timestamp <= {due_before} "
    if due_after is not None:
        limit += f"AND due_timestamp >= {due_after} "
    if min_priority is not None:
        limit += f"AND priority >= {min_priority} "
    if max_priority is not None:
        limit += f"AND priority <= {max_priority} "
    if min_bonus is not None:
        limit += f"AND bonus >= {min_bonus} "
    if max_bonus is not None:
        limit += f"AND bonus <= {max_bonus} "
    if assign_mode is not None:
        limit += f"AND assign_mode = {assign_mode} "

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    if order_by not in ["priority", "taskid", "title", "bonus", "due_timestamp", "create_timestamp"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}
    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}

    has_staff_perm = checkPerm(app, au["roles"], ["administrator", "manage_public_tasks"])
    if not has_staff_perm and (assign_to_userid is not None or assign_to_roleid is not None):
        response.status_code = 403
        return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}
    if assign_to_userid is not None and assign_to_roleid is not None:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "assign_to_userid, assign_to_roleid"})}
    if assign_to_roleid is not None:
        if assign_mode is None:
            assign_mode = 2
        else:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_value", var = {"key": "assign_mode"})}

    terms = "taskid, title, description, priority, bonus, due_timestamp, remind_timestamp, recurring, assign_mode, assign_to, mark_completed, mark_note, confirm_completed, confirm_note, userid"
    if assign_to_userid is not None:
        assign_to_user_roles = (await GetUserInfo(request=request, userid=assign_to_userid))["roles"]
        role_find_set = " OR ".join([f"FIND_IN_SET ('{role}', assign_to)" for role in assign_to_user_roles])
    else:
        role_find_set = " OR ".join([f"FIND_IN_SET ('{role}', assign_to)" for role in au["roles"]])
    perm_check = f"((assign_mode=0 AND userid={au['userid']}) OR (assign_mode=1 AND FIND_INT_SET('{au['userid']}', assign_to)) OR (assign_mode=2 AND ({role_find_set})))"
    if assign_to_userid is None and has_staff_perm:
        perm_check = "taskid >= 0"
    if assign_to_roleid is not None:
        limit += f"AND FIND_IN_SET('{assign_to_roleid}', assign_to) "

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT {terms} FROM task WHERE {perm_check} {limit} ORDER BY {order_by} {order}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_taskid is not None:
        for tt in t:
            if tt[0] == after_taskid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT {terms} FROM task WHERE {perm_check} {limit} ORDER BY {order_by} {order}, taskid DESC LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for i in range(len(t)):
        tt = t[i]
        (taskid, title, description, priority, bonus, due_timestamp, remind_timestamp, recurring, assign_mode, assign_to, mark_completed, mark_note, confirm_completed, confirm_note, creator_userid) = tt
        description = decompress(description)
        ret.append({"taskid": taskid, "title": title, "description": description, "priority": priority, "bonus": bonus, "due_timestamp": due_timestamp, "remind_timestamp": remind_timestamp, "recurring": recurring, "assign_mode": assign_mode, "assign_to": assign_to, "mark_completed": mark_completed, "mark_note": mark_note, "confirm_completed": confirm_completed, "confirm_note": confirm_note, "creator": await GetUserInfo(request, userid = creator_userid)})

    return {"list": ret, "total_items": tot, "total_pages": math.ceil(tot/page_size)}

async def get_task(request: Request, response: Response, taskid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /tasks', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT title, description, priority, bonus, due_timestamp, remind_timestamp, recurring, assign_mode, assign_to, mark_completed, mark_note, confirm_completed, confirm_note, userid FROM task WHERE taskid = {taskid};")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "task_not_found", force_lang = au["language"])}
    (title, description, priority, bonus, due_timestamp, remind_timestamp, recurring, assign_mode, assign_to, mark_completed, mark_note, confirm_completed, confirm_note, creator_userid) = t[0]

    if assign_mode == 0 and au["userid"] != creator_userid or \
        assign_mode == 1 and au["userid"] not in str2list(assign_to) or \
            assign_mode == 2 and not any([role in au["roles"] for role in str2list(assign_to)]):
        if not checkPerm(app, au["roles"], ["administrator", "manage_public_tasks"]):
            response.status_code = 403
            return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    description = decompress(description)

    return {"taskid": taskid, "title": title, "description": description, "priority": priority, "bonus": bonus, "due_timestamp": due_timestamp, "remind_timestamp": remind_timestamp, "recurring": recurring, "assign_mode": assign_mode, "assign_to": assign_to, "mark_completed": mark_completed, "mark_note": mark_note, "confirm_completed": confirm_completed, "confirm_note": confirm_note, "creator": await GetUserInfo(request, userid = creator_userid)}

async def post_task(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /tasks', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    data = await request.json()
    try:
        title = data["title"]
        if len(title) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        description = data["description"]
        if len(description) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}

        priority = int(data["priority"])
        if abs(priority) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "priority", "limit": "2,147,483,647"}, force_lang = au["language"])}
        bonus = int(data["bonus"])
        if abs(bonus) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "bonus", "limit": "2,147,483,647"}, force_lang = au["language"])}
        due_timestamp = int(data["due_timestamp"])
        if abs(due_timestamp) > 9223372036854775807:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "due_timestamp", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}
        remind_timestamp = int(data["remind_timestamp"])
        if abs(remind_timestamp) > 9223372036854775807:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "remind_timestamp", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}
        recurring = int(data["recurring"])
        if abs(recurring) > 9223372036854775807:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "recurring", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}

        assign_mode = data["assign_mode"]
        if assign_mode not in [0, 1, 2]:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_value", var = {"key": "assign_mode"}, force_lang = au["language"])}
        assign_to = data["assign_to"]
        if not isinstance(assign_to, list) or any([not isinstance(i, int) for i in assign_to]):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_value", var = {"key": "assign_to"}, force_lang = au["language"])}
        if assign_mode == 0 and assign_to != [au["userid"]]:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_value", var = {"key": "assign_to"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if assign_mode != 0 or bonus > 0:
        if not checkPerm(app, au["roles"], ["administrator", "manage_public_tasks"]):
            response.status_code = 403
            return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    await app.db.execute(dhrid, f"INSERT INTO task(userid, title, description, priority, bonus, create_timestamp,  due_timestamp, remind_timestamp, recurring, assign_mode, assign_to, mark_completed, mark_note, confirm_completed, confirm_note) VALUES ({au['userid']}, '{convertQuotation(title)}', '{convertQuotation(compress(description))}', {priority}, {bonus}, {int(time.time())}, {due_timestamp}, {remind_timestamp}, {recurring}, {assign_mode}, ',{list2str(assign_to)},', 0, '', 0, '');")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    taskid = (await app.db.fetchone(dhrid))[0]
    await AuditLog(request, au["uid"], "task", ml.ctr(request, "created_task", var = {"id": taskid}))
    await app.db.commit(dhrid)

    # TODO: Notify relevant users about the new task

    return {"taskid": taskid}

async def patch_task(request: Request, response: Response, taskid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /tasks', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT title, description, priority, bonus, due_timestamp, remind_timestamp, recurring, assign_mode, assign_to, userid FROM task WHERE taskid = {taskid};")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "task_not_found", force_lang = au["language"])}
    (title, description, priority, bonus, due_timestamp, remind_timestamp, recurring, assign_mode, assign_to, creator_userid) = t[0]
    description = decompress(description)

    data = await request.json()
    try:
        if "title" in data.keys():
            title = data["title"]
            if len(title) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if "description" in data.keys():
            description = data["description"]
            if len(description) > 2000:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}

        if "priority" in data.keys():
            priority = int(data["priority"])
            if abs(priority) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "priority", "limit": "2,147,483,647"}, force_lang = au["language"])}
        if "bonus" in data.keys():
            bonus = int(data["bonus"])
            if abs(bonus) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "bonus", "limit": "2,147,483,647"}, force_lang = au["language"])}
        if "due_timestamp" in data.keys():
            due_timestamp = int(data["due_timestamp"])
            if abs(due_timestamp) > 9223372036854775807:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "due_timestamp", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}
        if "remind_timestamp" in data.keys():
            remind_timestamp = int(data["remind_timestamp"])
            if abs(remind_timestamp) > 9223372036854775807:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "remind_timestamp", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}
        if "recurring" in data.keys():
            recurring = int(data["recurring"])
            if abs(recurring) > 9223372036854775807:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "recurring", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}

        if "assign_mode" in data.keys():
            assign_mode = data["assign_mode"]
            if assign_mode not in [0, 1, 2]:
                response.status_code = 400
                return {"error": ml.tr(request, "invalid_value", var = {"key": "assign_mode"}, force_lang = au["language"])}
        if "assign_to" in data.keys():
            assign_to = data["assign_to"]
            if not isinstance(assign_to, list) or any([not isinstance(i, int) for i in assign_to]):
                response.status_code = 400
                return {"error": ml.tr(request, "invalid_value", var = {"key": "assign_to"}, force_lang = au["language"])}
        if assign_mode == 0 and assign_to != [au["userid"]]:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_value", var = {"key": "assign_to"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if assign_mode != 0 or bonus > 0 or au["userid"] != creator_userid:
        if not checkPerm(app, au["roles"], ["administrator", "manage_public_tasks"]):
            response.status_code = 403
            return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE task SET title = '{convertQuotation(title)}', description = '{convertQuotation(compress(description))}', priority = {priority}, bonus = {bonus}, due_timestamp = {due_timestamp}, remind_timestamp = {remind_timestamp}, recurring = {recurring}, assign_mode = {assign_mode}, assign_to = ',{list2str(assign_to)},' WHERE taskid = {taskid};")
    await app.db.commit(dhrid)

    await AuditLog(request, au["uid"], "task", ml.ctr(request, "updated_task", var = {"id": taskid}))

    return Response(status_code = 204)

async def delete_task(request: Request, response: Response, taskid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'DELETE /tasks', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return

    await app.db.execute(dhrid, f"SELECT userid FROM task WHERE taskid = {taskid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "task_not_found", force_lang = au["language"])}

    if au["userid"] != t[0][0]:
        if not checkPerm(app, au["roles"], ["administrator", "manage_public_tasks"]):
            response.status_code = 403
            return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM task WHERE taskid = {taskid}")
    await AuditLog(request, au["uid"], "task", ml.ctr(request, "deleted_task", var = {"id": taskid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def put_task_complete(request: Request, response: Response, taskid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PUT /tasks/complete', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return

    data = await request.json()
    try:
        note = ""
        if note in data.keys():
            note = data["note"]
        if len(note) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "note", "limit": "2,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT mark_completed, confirm_completed, assign_mode, assign_to, userid FROM task WHERE taskid = {taskid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "task_not_found", force_lang = au["language"])}
    (mark_completed, confirm_completed, assign_mode, assign_to, creator_userid) = t[0]

    if assign_mode == 0 and au["userid"] != creator_userid or \
        assign_mode == 1 and au["userid"] not in str2list(assign_to) or \
            assign_mode == 2 and not any([role in au["roles"] for role in str2list(assign_to)]):
        response.status_code = 403
        return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    if mark_completed == 1:
        response.status_code = 400
        return {"error": ml.tr(request, "task_already_marked_as_completed", force_lang = au["language"])}
    if confirm_completed == 1:
        response.status_code = 400
        return {"error": ml.tr(request, "task_already_confirmed_as_completed", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE task SET mark_completed = 1, mark_note = '{convertQuotation(note)}' WHERE taskid = {taskid}")
    await app.db.commit(dhrid)

    # TODO: Notify task creator about the changes

    await AuditLog(request, au["uid"], "task", ml.ctr(request, "task_marked_as_completed", var = {"id": taskid}))

    return Response(status_code=204)

async def delete_task_complete(request: Request, response: Response, taskid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'DELETE /tasks/complete', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return

    data = await request.json()
    try:
        note = ""
        if note in data.keys():
            note = data["note"]
        if len(note) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "note", "limit": "2,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT mark_completed, confirm_completed, assign_mode, assign_to, userid FROM task WHERE taskid = {taskid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "task_not_found", force_lang = au["language"])}
    (mark_completed, confirm_completed, assign_mode, assign_to, creator_userid) = t[0]

    if assign_mode == 0 and au["userid"] != creator_userid or \
        assign_mode == 1 and au["userid"] not in str2list(assign_to) or \
            assign_mode == 2 and not any([role in au["roles"] for role in str2list(assign_to)]):
        response.status_code = 403
        return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    if mark_completed == 0:
        response.status_code = 400
        return {"error": ml.tr(request, "task_not_marked_as_completed", force_lang = au["language"])}
    if confirm_completed == 1:
        response.status_code = 400
        return {"error": ml.tr(request, "task_already_confirmed_as_completed", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE task SET mark_completed = 0, mark_note = '{convertQuotation(note)}' WHERE taskid = {taskid}")
    await app.db.commit(dhrid)

    # TODO: Notify task creator about the changes

    await AuditLog(request, au["uid"], "task", ml.ctr(request, "task_unmarked_as_completed", var = {"id": taskid}))

    return Response(status_code=204)

async def patch_task_status(request: Request, response: Response, taskid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /tasks/status', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return

    data = await request.json()
    try:
        status = data["status"]
        if status not in [0, 1]: # 0 = not completed | 1 = completed
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_value", var = {"key": "status"}, force_lang = au["language"])}

        note = ""
        if note in data.keys():
            note = data["note"]
        if len(note) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "note", "limit": "2,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT confirm_completed, assign_mode, userid FROM task WHERE taskid = {taskid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "task_not_found", force_lang = au["language"])}
    (confirm_completed, assign_mode, creator_userid) = t[0]

    if assign_mode == 0 and au["userid"] != creator_userid or \
            assign_mode in [1,2] and not checkPerm(app, au["roles"], ["administrator", "manage_public_tasks"]):
        response.status_code = 403
        return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    if status == 1 and confirm_completed == 1:
        response.status_code = 400
        return {"error": ml.tr(request, "task_already_confirmed_as_completed", force_lang = au["language"])}
    if status == 0 and confirm_completed == 0:
        response.status_code = 400
        return {"error": ml.tr(request, "task_not_confirmed_as_completed", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE task SET confirm_completed = {status}, confirm_note = '{convertQuotation(note)}' WHERE taskid = {taskid}")
    await app.db.commit(dhrid)

    # TODO: Distribute bonus points and notify relevant users

    text_status = ml.ctr(request, "completed") if status == 1 else ml.ctr(request, "uncompleted")
    await AuditLog(request, au["uid"], "task", ml.ctr(request, "updated_task_status", var = {"id": taskid, "status": text_status}))

    return Response(status_code=204)
