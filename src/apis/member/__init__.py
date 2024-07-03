# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

import apis.member.info as info
import apis.member.manage as manage
import apis.member.userop as userop

routes = [
    APIRoute("/member/roles", info.get_roles, methods=["GET"], response_class=JSONResponse),
    APIRoute("/member/ranks", info.get_ranks, methods=["GET"], response_class=JSONResponse),
    APIRoute("/member/perms", info.get_perms, methods=["GET"], response_class=JSONResponse),
    APIRoute("/member/list", info.get_list, methods=["GET"], response_class=JSONResponse),

    APIRoute("/member/roles/rank", userop.patch_roles_rank_default, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/member/roles/rank/{rank_type_id}", userop.patch_roles_rank, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/member/bonus/history", userop.get_bonus_history, methods=["GET"], response_class=JSONResponse),
    APIRoute("/member/bonus/claim", userop.post_bonus_claim, methods=["POST"], response_class=JSONResponse),
    APIRoute("/member/bonus/notification/settings", userop.get_bonus_notification_settings, methods=["GET"], response_class=JSONResponse),
    APIRoute("/member/bonus/notification/settings", userop.patch_bonus_notification_settings, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/member/roles/history/{historyid}", userop.delete_role_history, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/member/resign", userop.post_resign, methods=["POST"], response_class=JSONResponse),

    APIRoute("/member/{userid}/roles", manage.patch_roles, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/member/{userid}/points", manage.patch_points, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/member/{userid}/dismiss", manage.post_dismiss, methods=["POST"], response_class=JSONResponse)
]

routes_banner = [
    APIRoute("/member/banner", info.get_banner, methods=["GET"], response_class=JSONResponse),
]
