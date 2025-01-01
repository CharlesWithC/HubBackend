# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

import plugins.announcement as announcement
import plugins.application as application
import plugins.challenge as challenge
import plugins.division as division
import plugins.downloads as downloads
import plugins.economy as economy
import plugins.event as event
import plugins.poll as poll
import plugins.task as task

routes_announcement = [
    APIRoute("/announcements/types", announcement.get_types, methods=["GET"], response_class=JSONResponse),
    APIRoute("/announcements/list", announcement.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/announcements/{announcementid}", announcement.get_announcement, methods=["GET"], response_class=JSONResponse),
    APIRoute("/announcements", announcement.post_announcement, methods=["POST"], response_class=JSONResponse),
    APIRoute("/announcements/{announcementid}", announcement.patch_announcement, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/announcements/{announcementid}", announcement.delete_announcement, methods=["DELETE"], response_class=JSONResponse)
]

routes_application = [
    APIRoute("/applications/types", application.get_types, methods=["GET"], response_class=JSONResponse),
    APIRoute("/applications/list", application.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/applications/{applicationid}", application.get_application, methods=["GET"], response_class=JSONResponse),
    APIRoute("/applications", application.post_application, methods=["POST"], response_class=JSONResponse),
    APIRoute("/applications/{applicationid}/message", application.post_message, methods=["POST"], response_class=JSONResponse),
    APIRoute("/applications/{applicationid}/status", application.patch_status, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/applications/{applicationid}", application.delete_application, methods=["DELETE"], response_class=JSONResponse)
]

routes_challenge = [
    APIRoute("/challenges/list", challenge.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/challenges/{challengeid}", challenge.get_challenge, methods=["GET"], response_class=JSONResponse),
    APIRoute("/challenges", challenge.post_challenge, methods=["POST"], response_class=JSONResponse),
    APIRoute("/challenges/{challengeid}", challenge.patch_challenge, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/challenges/{challengeid}", challenge.delete_challenge, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/challenges/{challengeid}/delivery/{logid}", challenge.put_delivery, methods=["PUT"], response_class=JSONResponse),
    APIRoute("/challenges/{challengeid}/delivery/{logid}", challenge.delete_delivery, methods=["DELETE"], response_class=JSONResponse),
]

routes_division = [
    APIRoute("/divisions/list", division.get_all_divisions, methods=["GET"], response_class=JSONResponse),
    APIRoute("/divisions/statistics", division.get_divisions_statistics, methods=["GET"], response_class=JSONResponse),
    APIRoute("/divisions/{divisionid}/activity", division.get_divisions_activity, methods=["GET"], response_class=JSONResponse),
    APIRoute("/dlog/{logid}/division", division.get_dlog_division, methods=["GET"], response_class=JSONResponse),
    APIRoute("/dlog/{logid}/division/{divisionid}", division.post_dlog_division, methods=["POST"], response_class=JSONResponse),
    APIRoute("/dlog/{logid}/division/{divisionid}", division.patch_dlog_division, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/divisions/list/pending", division.get_list_pending, methods=["GET"], response_class=JSONResponse)
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
    APIRoute("/economy", economy.get_economy, methods=["GET"], response_class=JSONResponse),

    APIRoute("/economy/balance/leaderboard", economy.get_balance_leaderboard, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/balance/transfer", economy.post_balance_transfer, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/balance", economy.get_balance, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/balance/{userid}", economy.get_balance, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/balance/{userid}", economy.patch_balance, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/economy/balance/{userid}/transactions/list", economy.get_balance_transaction_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/balance/{userid}/transactions/export", economy.get_balance_transaction_export, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/balance/{userid}/visibility/{visibility}", economy.post_balance_visibility, methods=["POST"], response_class=JSONResponse),

    APIRoute("/economy/garages", economy.get_all_garages, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/garages/list", economy.get_garage_list, methods=["GET"], response_class=JSONResponse),
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
    APIRoute("/economy/trucks/list", economy.get_truck_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}", economy.get_truck, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}/{operation}/history", economy.get_truck_operation_history, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{truckid}/purchase", economy.post_truck_purchase, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}/transfer", economy.post_truck_transfer, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}/relocate", economy.post_truck_relocate, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}/activate", economy.post_truck_activate, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}/deactivate", economy.post_truck_deactivate, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}/repair", economy.post_truck_repair, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}/sell", economy.post_truck_sell, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/trucks/{vehicleid}/scrap", economy.post_truck_scrap, methods=["POST"], response_class=JSONResponse),

    APIRoute("/economy/merch", economy.get_all_merch, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/merch/list", economy.get_merch_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/economy/merch/{merchid}/purchase", economy.post_merch_purchase, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/merch/{itemid}/transfer", economy.post_merch_transfer, methods=["POST"], response_class=JSONResponse),
    APIRoute("/economy/merch/{itemid}/sell", economy.post_merch_sell, methods=["POST"], response_class=JSONResponse)
]

routes_event = [
    APIRoute("/events/list", event.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/events/{eventid}", event.get_event, methods=["GET"], response_class=JSONResponse),
    APIRoute("/events/{eventid}/vote", event.put_vote, methods=["PUT"], response_class=JSONResponse),
    APIRoute("/events/{eventid}/vote", event.delete_vote, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/events", event.post_event, methods=["POST"], response_class=JSONResponse),
    APIRoute("/events/{eventid}", event.patch_event, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/events/{eventid}", event.delete_event, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/events/{eventid}/attendees", event.patch_attendees, methods=["PATCH"], response_class=JSONResponse)
]

routes_poll = [
    APIRoute("/polls/list", poll.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/polls/{pollid}", poll.get_poll, methods=["GET"], response_class=JSONResponse),
    APIRoute("/polls/{pollid}/vote", poll.put_poll_vote, methods=["PUT"], response_class=JSONResponse),
    APIRoute("/polls/{pollid}/vote", poll.patch_poll_vote, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/polls/{pollid}/vote", poll.delete_poll_vote, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/polls", poll.post_poll, methods=["POST"], response_class=JSONResponse),
    APIRoute("/polls/{pollid}", poll.patch_poll, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/polls/{pollid}", poll.delete_poll, methods=["DELETE"], response_class=JSONResponse)
]

routes_task = [
    APIRoute("/tasks/list", task.get_task_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/tasks/{taskid}", task.get_task, methods=["GET"], response_class=JSONResponse),
    APIRoute("/tasks", task.post_task, methods=["POST"], response_class=JSONResponse),
    APIRoute("/tasks/{taskid}", task.patch_task, methods=["PATCH"], response_class=JSONResponse),
    APIRoute("/tasks/{taskid}", task.delete_task, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/tasks/{taskid}/complete/mark", task.put_task_complete_mark, methods=["PUT"], response_class=JSONResponse),
    APIRoute("/tasks/{taskid}/complete/mark", task.delete_task_complete_mark, methods=["DELETE"], response_class=JSONResponse),
    APIRoute("/tasks/{taskid}/complete/accept", task.post_task_complete_accept, methods=["POST"], response_class=JSONResponse),
    APIRoute("/tasks/{taskid}/complete/reject", task.post_task_complete_reject, methods=["POST"], response_class=JSONResponse)
]
