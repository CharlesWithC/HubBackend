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
# PATCH /tasks/{taskid}/status (creator-patch)

# Background tasks
# Notification on task create
# Reminder on remind-at
# Update due-date & remind-at if recurring


from fastapi import Header, Request, Response

import multilang as ml
from functions import *


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

    await app.db.execute(dhrid, f"INSERT INTO task(userid, title, description, priority, bonus, due_timestamp, remind_timestamp, recurring, assign_mode, assign_to, mark_completed, confirm_completed) VALUES ({au['userid']}, '{convertQuotation(title)}', '{convertQuotation(compress(description))}', {priority}, {bonus}, {due_timestamp}, {remind_timestamp}, {recurring}, {assign_mode}, ',{list2str(assign_to)},', '', '');")
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

    await app.db.execute(dhrid, f"SELECT title, description, priority, bonus, due_timestamp, remind_timestamp, recurring, assign_mode, assign_to, mark_completed, confirm_completed, userid FROM task WHERE taskid = {taskid};")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "task_not_found", force_lang = au["language"])}
    (title, description, priority, bonus, due_timestamp, remind_timestamp, recurring, assign_mode, assign_to, mark_completed, confirm_completed, creator_userid) = t[0]
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
