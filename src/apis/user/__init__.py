# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import apis.user.connections as connections
import apis.user.info as info
import apis.user.language as language
import apis.user.manage as manage
import apis.user.mfa as mfa
import apis.user.notification as notification
import apis.user.password as password

from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse

routes = [
    APIRoute("/user/list", info.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/user/profile", info.get_profile, methods=["GET"], response_class=JSONResponse),
    APIRoute("/user/profile", info.patch_profile, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/user/bio", info.patch_bio, methods=["PATCH"], response_class=JSONResponse),
    
    APIRoute("/user/language", language.get_language, methods=["GET"], response_class=JSONResponse),
    APIRoute("/user/language", language.patch_language, methods=["PATCH"], response_class=JSONResponse),
    
    APIRoute("/user/password", password.patch_password, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/user/password/disable", password.post_password_disable, methods=["POST"], response_class=JSONResponse),

    APIRoute("/user/mfa/enable", mfa.post_enable, methods=["POST"], response_class=JSONResponse),
    APIRoute("/user/mfa/disable", mfa.post_disable, methods=["POST"], response_class=JSONResponse),
    
    APIRoute("/user/notification/list", notification.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/user/notification/settings", notification.get_settings, methods=["GET"], response_class=JSONResponse),
    APIRoute("/user/notification/settings/{notification_type}/enable", notification.post_settings_enable, methods=["POST"], response_class=JSONResponse),
    APIRoute("/user/notification/settings/{notification_type}/disable", notification.post_settings_disable, methods=["POST"], response_class=JSONResponse),
    # this has to be put in the end, due to the speciality of the path
    APIRoute("/user/notification/{notificationid}", notification.get_notification, methods=["GET"], response_class=JSONResponse),
    APIRoute("/user/notification/{notificationid}/status/{status}", notification.patch_status, methods=["PATCH"], response_class=JSONResponse),

    APIRoute("/user/{uid}/accept", manage.post_accept, methods=["POST"], response_class=JSONResponse),
    APIRoute("/user/{uid}/discord", manage.patch_discord, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/user/{uid}/connections", manage.delete_connections, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/user/ban/list", manage.get_ban_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/user/ban", manage.get_ban, methods=["GET"], response_class=JSONResponse),
    APIRoute("/user/ban", manage.put_ban, methods=["PUT"], response_class=JSONResponse),
    APIRoute("/user/ban", manage.delete_ban, methods=["DELETE"], response_class=JSONResponse),

    APIRoute("/user/resend-confirmation", connections.post_resend_confirmation, methods=["POST"], response_class=JSONResponse),
    APIRoute("/user/email", connections.patch_email, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/user/discord", connections.patch_discord, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/user/steam", connections.patch_steam, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/user/truckersmp", connections.patch_truckersmp, methods=["PATCH"], response_class=JSONResponse),
    
    # this has to be put in the end, due to the speciality of the path
    APIRoute("/user/{uid}", manage.delete_user, methods=["DELETE"], response_class=JSONResponse)
]