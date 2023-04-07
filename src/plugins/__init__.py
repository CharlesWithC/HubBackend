# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

import plugins.announcements as announcements
import plugins.applications as application
import plugins.challenges as challenges
import plugins.divisions as divisions
import plugins.downloads as downloads
import plugins.economy as economy
import plugins.events as events

routes_announcement = [
    APIRoute("/announcements/list", announcements.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/announcements/{announcementid}", announcements.get_announcement, methods=["GET"], response_class=JSONResponse),
    APIRoute("/announcements", announcements.post_announcement, methods=["POST"], response_class=JSONResponse),
    APIRoute("/announcements/{announcementid}", announcements.patch_announcement, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/announcements/{announcementid}", announcements.delete_announcement, methods=["DELETE"], response_class=JSONResponse)
]

routes_application = [
    APIRoute("/applications/types", application.get_types, methods=["GET"], response_class=JSONResponse),
    APIRoute("/applications/positions", application.get_positions, methods=["GET"], response_class=JSONResponse),
    APIRoute("/applications/positions", application.patch_application, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/applications/list", application.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/applications/{applicationid}", application.get_application, methods=["GET"], response_class=JSONResponse),
    APIRoute("/applications", application.post_application, methods=["POST"], response_class=JSONResponse),
    APIRoute("/applications/{applicationid}", application.patch_application, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/applications/{applicationid}/status", application.patch_status, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/applications/{applicationid}", application.delete_application, methods=["DELETE"], response_class=JSONResponse)
]

routes_challenge = [
    APIRoute("/challenges/list", challenges.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/challenges/{challengeid}", challenges.get_challenge, methods=["GET"], response_class=JSONResponse),
    APIRoute("/challenges", challenges.post_challenge, methods=["POST"], response_class=JSONResponse),
    APIRoute("/challenges/{challengeid}", challenges.patch_challenge, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/challenges/{challengeid}", challenges.delete_challenge, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/challenges/{challengeid}/delivery/{logid}", challenges.put_delivery, methods=["PUT"], response_class=JSONResponse),
    APIRoute("/challenges/{challengeid}/delivery/{logid}", challenges.delete_delivery, methods=["DELETE"], response_class=JSONResponse),
]

routes_division = [
    APIRoute("/divisions/list", divisions.get_all_divisions, methods=["GET"], response_class=JSONResponse),
    APIRoute("/divisions", divisions.get_division, methods=["GET"], response_class=JSONResponse),
    APIRoute("/dlog/{logid}/division", divisions.get_dlog_division, methods=["GET"], response_class=JSONResponse),
    APIRoute("/dlog/{logid}/division/{divisionid}", divisions.post_dlog_division, methods=["POST"], response_class=JSONResponse),
    APIRoute("/dlog/{logid}/division/{divisionid}", divisions.patch_dlog_division, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/divisions/list/pending", divisions.get_list_pending, methods=["GET"], response_class=JSONResponse)
]

routes_downloads = [
    APIRoute("/downloads/list", downloads.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/downloads/redirect/{secret}", downloads.get_redirect, methods=["GET"], response_class=JSONResponse),
    APIRoute("/downloads/{downloadsid}", downloads.get_downloads, methods=["GET"], response_class=JSONResponse),
    APIRoute("/downloads", downloads.post_downloads, methods=["POST"], response_class=JSONResponse),
    APIRoute("/downloads/{downloadsid}", downloads.patch_downloads, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/downloads/{downloadsid}", downloads.delete_downloads, methods=["DELETE"], response_class=JSONResponse)
]

routes_economy = [
    APIRoute("/economy/balance/leaderboard", economy.get_balance_leaderboard, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/balance/transfer", economy.post_balance_transfer, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/balance/{userid}", economy.get_balance, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/balance/{userid}/transactions/list", economy.get_balance_transaction_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/balance/{userid}/transactions/export", economy.get_balance_transaction_export, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/balance/{userid}/visibility/{visibility}", economy.post_balance_visibility, methods=["POST"], response_class=JSONResponse),
    
    APIRoute("/economy/garages", economy.get_all_garages, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/garages/list", economy.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/garages/{garageid}", economy.get_garage, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/garages/{garageid}/purchase", economy.post_garage_purchase, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/garages/{garageid}/transfer", economy.post_garage_transfer, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/garages/{garageid}/sell", economy.post_garage_sell, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/garages/{garageid}/slots/list", economy.get_garage_slots_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/garages/{garageid}/slots/{slotid}", economy.get_garage_slot, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/garages/{garageid}/slots/purchase", economy.post_garage_slot_purchase, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/garages/{garageid}/slots/{slotid}/transfer", economy.post_garage_slot_transfer, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/garages/{garageid}/slots/{slotid}/sell", economy.post_garage_slot_sell, methods=["POST"], response_class=JSONResponse),
    
    APIRoute("/economy/trucks", economy.get_all_trucks, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/trucks/list", economy.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}", economy.get_truck, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}/{operation}/history", economy.get_truck_operation_history, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{truckid}/purchase", economy.post_truck_purchase, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{truckid}/transfer", economy.post_truck_transfer, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{truckid}/relocate", economy.post_truck_relocate, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{truckid}/activate", economy.post_truck_activate, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{truckid}/deactivate", economy.post_truck_deactivate, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{truckid}/repair", economy.post_truck_repair, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{truckid}/sell", economy.post_truck_sell, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{truckid}/scrap", economy.post_truck_scrap, methods=["POST"], response_class=JSONResponse)
]

routes_event = [
    APIRoute("/events/list", events.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/events/{eventid}", events.get_event, methods=["GET"], response_class=JSONResponse),
    APIRoute("/events/{eventid}/vote", events.put_vote, methods=["PUT"], response_class=JSONResponse),
    APIRoute("/events/{eventid}/vote", events.delete_vote, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/events", events.post_event, methods=["POST"], response_class=JSONResponse),
    APIRoute("/events/{eventid}", events.patch_event, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/events/{eventid}", events.delete_event, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/events/{eventid}/attendees", events.patch_attendees, methods=["PATCH"], response_class=JSONResponse)
]