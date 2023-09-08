# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

import apis.auth.discord as discord
import apis.auth.generic as generic
import apis.auth.steam as steam
import apis.auth.ticket as ticket
import apis.auth.token as token

routes = [
    APIRoute("/auth/password", generic.post_password, methods=["POST"], response_class=JSONResponse),
    APIRoute("/auth/register", generic.post_register, methods=["POST"], response_class=JSONResponse),
    APIRoute("/auth/reset", generic.post_reset, methods=["POST"], response_class=JSONResponse),
    APIRoute("/auth/mfa", generic.post_mfa, methods=["POST"], response_class=JSONResponse),
    APIRoute("/auth/email", generic.post_email, methods=["POST"], response_class=JSONResponse),

    APIRoute("/auth/discord/callback", discord.get_callback, methods=["GET"], response_class=JSONResponse),

    APIRoute("/auth/steam/callback", steam.get_callback, methods=["GET"], response_class=JSONResponse),

    APIRoute("/auth/ticket", ticket.post_ticket, methods=["POST"], response_class=JSONResponse),
    APIRoute("/auth/ticket", ticket.get_ticket, methods=["GET"], response_class=JSONResponse),

    APIRoute("/token", token.get_token, methods=["GET"], response_class=JSONResponse),
    APIRoute("/token", token.patch_token, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/token", token.delete_token, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/token/list", token.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/token/hash", token.delete_hash, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/token/all", token.delete_all, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/token/application/list", token.get_application_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/token/application", token.post_application, methods=["POST"], response_class=JSONResponse),
    APIRoute("/token/application", token.delete_application, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/token/application/all", token.delete_application_all, methods=["DELETE"], response_class=JSONResponse)
]
