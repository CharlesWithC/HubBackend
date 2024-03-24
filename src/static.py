# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import inspect
import json
import os
import pytz

abspath = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename))
TRACKER = {"tracksim": "TrackSim", "trucky": "Trucky", "custom": "Custom"}

def load(app):
    app.roles = {} # sorted based on order_id
    sroles = app.config.roles
    for srole in sroles:
        try:
            app.roles[srole["id"]] = srole
        except:
            pass
    app.roles = dict(sorted(app.roles.items(), key=lambda x: x[1]["order_id"]))

    app.default_rank_type_point_types = []
    app.rank_type_point_types = {}
    app.ranktypes = {}
    for rt in app.config.rank_types:
        try:
            if rt["default"]:
                app.default_rank_type_point_types = rt["point_types"]
            app.rank_type_point_types[rt["id"]] = rt["point_types"]
            app.ranktypes[rt["id"]] = {}
            for t in rt["details"]:
                if t["discord_role_id"] is None:
                    t["discord_role_id"] = 0
                app.ranktypes[rt["id"]][t["points"]] = {"name": t["name"], "discord_role_id": t["discord_role_id"], "distance_bonus": t["distance_bonus"], "daily_bonus": t["daily_bonus"]}
            app.ranktypes[rt["id"]] = dict(sorted(app.ranktypes[rt["id"]].items(), key=lambda x: x[0]))
        except:
            pass

    app.division_roles = []
    for division in app.config.divisions:
        try:
            app.division_roles.append(division["role_id"])
        except:
            pass

    app.division_points = {}
    app.division_name = {}
    for division in app.config.divisions:
        app.division_points[division["id"]] = division["points"]
        app.division_name[division["id"]] = division["name"]

    app.trucks = {}
    app.garages = {}
    app.merch = {}
    for truck in app.config.__dict__["economy"].__dict__["trucks"]:
        app.trucks[truck["id"]] = truck
    for garage in app.config.__dict__["economy"].__dict__["garages"]:
        app.garages[garage["id"]] = garage
    for merch in app.config.__dict__["economy"].__dict__["merch"]:
        app.merch[merch["id"]] = merch

    return app

TF = {-1: False, 0: False, 1: True, "0": False, "1": True, "False": False, "True": True}

OPENAPI_RESPONSES = '"responses": {"200": {"content": {"application/json": {"schema": {"type": "object"}}},  "description": "Success"}}'

if os.path.exists(os.path.join(abspath, "openapi.json")):
    OPENAPI = json.loads(open(os.path.join(abspath, "openapi.json"), "r", encoding="utf-8").read().replace('"responses": {}', OPENAPI_RESPONSES))
else:
    OPENAPI = None

NOTIFICATION_SETTINGS = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "bonus": False, "new_announcement": False, "application": False, "new_challenge": False, "challenge": False, "division": False, "new_downloads": False, "economy": False, "new_event": False, "upcoming_event": False, "new_poll": False, "poll_result": False}

pytz.country_names.get("UTC") # ensure pytz loads all country_names first
ISO_COUNTRIES = pytz.country_names.__dict__["data"]
ISO_COUNTRIES["00"] = "Local Network"
ISO_COUNTRIES["XX"] = "Unknown Region"
ISO_COUNTRIES["T1"] = "Tor"
# 00 is added by me for Local Network
# XX and T1 are provided by CloudFlare, which are not in ISO standard

# Hard-coded English String Table
EN_STRINGTABLE = {
    "unknown_error": "Unknown Error",
    "service_api_error": "{service} API Error",
    "api_timeout": "API Timeout",
    "invalid_api_token": "Invalid API Token",
    "rate_limit": "Rate Limit Exceeded",
    "bad_json": "Invalid JSON: Missing Fields or Unparseable Data",
    "invalid_params": "Invalid Request Parameters",
    "content_too_long": "Maximum length of \"{item}\" is {limit} characters.",
    "value_too_large": "Maximum value of \"{item}\" is {limit}.",
    "attention_required": "Attention Required",
    "invalid_discord_token": "Invalid Discord Bot Token: Discord Integration disabled temporarily. Set a valid token in config and reload config to restore the functionality.",

    "invalid_captcha": "Invalid Captcha",
    "captcha_api_inaccessible": "Captcha API Inaccessible",
    "invalid_email_or_password": "Invalid Email or Password",
    "invalid_authorization_token": "Invalid Authorization Token",
    "unknown_authorization_token_type": "Unknown Authorization Token Type",
    "invalid_hash": "Invalid Hash",
    "invalid_userid": "Invalid User ID",
    "invalid_timezone": "Invalid Timezone",
    "invalid_link": "Invalid Link",

    "unauthorized": "Unauthorized Access",
    "no_access_to_resource": "Insufficient Permissions to Access Resource",
    "application_token_not_allowed": "Access Denied: Application Token Not Allowed",
    "access_sensitive_data": "Access Denied: Login with Discord, Steam, or enable MFA to access sensitive data.",
    "mfa_required": "Access Denied: Enable MFA and provide OTP to proceed.",
    "connect_more_to_disable_password": "Access Denied: Connect Discord or Steam account before disabling password login.",

    "ban_with_expire": "You are banned {expire}",
    "ban_with_reason_expire": "You are banned for {reason} {expire}",
    "user_pending_deletion": "Your account is pending deletion. Please log in again to recover your account.",
    "user_in_guild_check_failed": "Failed to check if the user is in the Discord server.",
    "current_user_in_guild_check_failed": "Failed to check if you are in the Discord server.",
    "user_didnt_join_discord": "The user has not joined the Discord server.",
    "current_user_didnt_join_discord": "You have not joined the Discord server.",
    "email_not_unique": "Your email is connected to multiple users, thus you cannot enable password login.",
    "weak_password": "Password Too Weak",
    "invalid_mfa_secret": "Invalid MFA Secret",
    "mfa_already_enabled": "MFA Already Enabled",
    "mfa_not_enabled": "MFA Not Enabled",
    "invalid_otp": "Invalid OTP",
    "language_not_supported": "Language Not Supported",
    "invalid_avatar_url": "Invalid Avatar URL",
    "avatar_domain_not_whitelisted": "Avatar Domain Not Whitelisted",
    "smtp_configuration_invalid": "SMTP Configuration Invalid: Can't Send Email",
    "role_history_not_found": "Role History Not Found",
    "ban_history_not_found": "Ban History Not Found",

    "connection_not_found": "{app} account is not connected.",
    "connection_conflict": "{app} account already connected to another user.",
    "connection_invalid": "{app} account connection is invalid.",

    "no_pending_email_confirmation": "No Pending Email Confirmation",
    "connections_linked_to_multiple_users": "The connections provided are linked to multiple users. To avoid unexpected bans, only connections for a single user are accepted.",
    "dismiss_before_ban": "Dismiss Member Before Banning",
    "dismiss_before_delete": "Dismiss Member Before Deleting Account",
    "resign_before_delete": "Resign Before Deleting Account",
    "user_already_banned": "User Already Banned",
    "user_not_banned": "User Not Banned",
    "unable_to_dm": "Failed to enable Discord notification: Unable to DM.",
    "custom_profile_disabled": "Custom Profile Disabled",
    "already_claimed_todays_bonus": "You have already claimed today's bonus points!",
    "claimed_daily_bonus": "You claimed `{points}` daily bonus points.",
    "claimed_daily_bonus_with_streak": "You kept `{streak}` day of streak and claimed `{points}` daily bonus points.",
    "claimed_daily_bonus_with_streak_s": "You kept `{streak}` days of streak and claimed `{points}` daily bonus points.",
    "daily_bonus_not_available": "Daily Bonus is not available for your rank.",

    "steam_api_key_not_configured": "Steam API Key Not Configured",
    "invalid_steam_auth": "Invalid Steam Authentication",
    "invalid_truckersmp_id": "Invalid TruckersMP ID",
    "must_connect_steam_before_truckersmp": "Steam account must be connected before connecting TruckersMP account.",
    "truckersmp_steam_mismatch": "Steam account connected to TruckersMP user {truckersmp_name} ({truckersmpid}) does not match your Steam account.",

    "user_not_found": "User Not Found",
    "member_not_found": "Member Not Found",
    "banner_service_unavailable": "Banner Service Unavailable",
    "role_not_found": "One or more role to add or remove is not found.",
    "banned_user_cannot_be_accepted": "Banned users cannot be accepted as members.",
    "user_is_already_member": "User is already a member.",
    "user_exists_with_new_connections": "The connections are already linked to other users. Delete them to proceed.",
    "user_position_higher_or_equal": "User's highest role is higher than or equal to yours.",
    "add_role_higher_or_equal": "You are not allowed to add a role higher than or equal to your highest role.",
    "remove_role_higher_or_equal": "You are not allowed to remove a role higher than or equal to your highest role.",
    "already_have_rank_role": "The rank role has already been given in Discord.",
    "losing_admin_permission": "Role Update Rejected: You will lose administrator permission.",

    "delivery": "Delivery",
    "driver": "Driver",
    "truck": "Truck",
    "cargo": "Cargo",
    "from": "From",
    "to": "To",
    "distance": "Distance",
    "fuel": "Fuel",
    "net_profit": "Net Profit",
    "xp_earned": "XP Earned",
    "time_spent": "Time Spent",
    "single_player": "Single Player",
    "scs_convoy": "SCS Convoy",
    "delivery_log_not_found": "Delivery Log Not Found",

    "invalid_distance_unit": "Invalid Distance Unit: Only \"metric\" and \"imperial\" is accepted.",
    "invalid_value": "Invalid value for {key}",
    "config_value_is_empty": "Invalid value for \"{item}\": Must not be empty.",
    "config_invalid_distance_unit": "Invalid value for \"distance_unit\": Must be \"metric\" or \"imperial\".",
    "config_invalid_tracker": "Invalid value for \"tracker\": Must be \"trucky\", \"tracksim\" or \"custom\".",
    "config_invalid_datatype_boolean": "Invalid data type for \"{item}\": Must be boolean.",
    "config_invalid_datatype_integer": "Invalid data type for \"{item}\": Must be integer.",
    "config_invalid_hex_color": "Invalid value for \"hex_color\": Must be a hex string of 6 characters.",
    "config_invalid_data_url": "Invalid data type for \"{item}\": Must be a valid URL.",
    "config_invalid_permission_admin_not_found": "Invalid value for \"perms\": \"administrator\" permission not found.",
    "config_invalid_permission_admin_protection": "Permission Update Rejected: New \"administrator\" permission does not include any role the current user has.",
    "no_config_reload_available": "No new config has been saved. Unable to reload config.",
    "discord_integrations_disabled": "Discord Integrations Disabled Temporarily: Invalid Discord Bot Token",
    "discord_api_inaccessible": "Discord API Inaccessible",

    "announcement_not_found": "Announcement Not Found",
    "unknown_announcement_type": "Unknown Announcement Type",
    "new_announcement_with_title": "New Announcement: `{title}`",
    "new_announcement": "New Announcement",
    "author": "Author",

    "unknown_application_type": "Unknown Application Type",
    "status": "Status",
    "time": "Time",
    "message": "Message",
    "no_message": "No Message",
    "pending": "Pending",
    "accepted": "Accepted",
    "declined": "Declined",

    "application_not_found": "Application Not Found",
    "applicant_not_eligible": "You are ineligible to submit this type of application.",
    "no_multiple_application": "You cannot submit multiple applications of this type within {count} hours.",
    "same_type_application_exists": "You cannot submit another application of this type when there is a pending one.",
    "no_permission_to_application_type": "You lack permission to access this type of application.",
    "must_have_connection": "{app} account must be connected before submitting an application.",
    "not_applicant": "You are not the applicant of the application.",
    "application_already_accepted": "Application Already Accepted",
    "application_already_declined": "Application Already Declined",
    "application_already_processed": "Application Already Processed (Status Unknown)",
    "application_message_too_long": "Message Too Long: Please view the application on the Drivers Hub.",

    "start_time_must_be_earlier_than_end_time": "Start time must be earlier than end time.",
    "invalid_challenge_type": "Invalid Challenge Type",
    "invalid_required_roles": "Invalid Required Roles",
    "invalid_reward_points": "Reward points must not be negative.",
    "invalid_delivery_count": "Delivery count must not be negative or zero.",
    "invalid_distance_sum": "Distance sum must not be negative or zero.",
    "challenge_not_found": "Challenge Not Found",
    "challenge_delivery_not_found": "The delivery is not accepted for the challenge.",
    "challenge_delivery_already_accepted": "The delivery is already accepted for the challenge.",
    "new_challenge_with_title": "New Challenge: `{title}`",
    "new_challenge": "New Challenge",
    "start": "Start",
    "end": "End",
    "reward_points": "Reward Points",

    "only_delivery_submitter_can_request_division_validation": "Only the user who completed the delivery is allowed to submit division validation request.",
    "division_already_requested": "A division validation request has already been submitted.",
    "division_already_validated": "Delivery Already Validated",
    "division_already_denied": "The delivery validation request has been denied and you cannot request again.",
    "not_division_driver": "You are not a driver for the division.",
    "division_validation_not_found": "Delivery Validation Request Not Found",
    "division_not_validated": "Delivery Not Validated",

    "downloads_not_found": "Downloadable item Not Found",
    "new_downloadable_item_with_title": "New Downloadable Item: `{title}`",
    "new_downloadable_item": "New Downloadable Item",
    "download_link": "[Download]({link})",

    "event_not_found": "Event Not Found",
    "event_notification": "Event Notification",
    "event_notification_description": "This event is starting soon!",
    "event_starting": "Event `{title}` (Event ID: `{eventid}`) is starting soon!",
    "event_not_voted": "Event Not Voted",
    "event_already_voted": "Event Already Voted",
    "title": "Title",
    "departure": "Departure",
    "destination": "Destination",
    "meetup_time": "Meetup Time",
    "departure_time": "Departure Time",
    "new_event_with_title": "New Event: `{title}`",
    "new_event": "New Event",

    "poll_not_found": "Poll Not Found",
    "poll_already_ended": "Poll Already Ended",
    "selected_too_many_choices": "You have selected too many choices, up to {count} is allowed.",
    "selected_invalid_choice": "You have selected at least one invalid choice.",
    "modify_vote_not_allowed": "You are not allowed to modify your votes.",
    "user_already_voted": "You have already voted.",
    "user_not_voted": "You have not voted yet.",
    "new_poll_with_title": "New Poll: `{title}`",
    "new_poll": "New Poll",
    "choices": "Choices",
    "poll_result": "Poll Result",
    "poll_ended_with_title": "Poll Ended: `{title}`",

    "garage": "garage",
    "garage_slot": "garage slot",
    "economy_truck": "truck",
    "merch": "merch",
    "purchase_forbidden": "You are not allowed to purchase a {item}.",
    "purchase_company_forbidden": "You are not allowed to purchase a {item} for the company.",
    "modify_forbidden": "You are not allowed to modify the {item}.",
    "truck_not_found": "Truck Not Found",
    "truck_history_forbidden": "You do not have access to the truck's history data.",
    "invalid_owner": "Invalid Owner",
    "insufficient_balance": "Insufficient Balance",
    "garage_slot_not_found": "Garage Slot Not Found",
    "garage_slot_occupied": "Garage Slot Occupied",
    "new_owner_conflict": "The new owner must not be the same as the current owner.",
    "truck_repair_required": "The truck must be repaired before it can be activated.",
    "truck_scrap_required": "The truck has reached its mileage limit and must be scrapped.",
    "truck_scrap_unncessary": "The truck is far from its mileage limit and cannot be scrapped.",
    "company": "Company",
    "dealership": "Dealership",
    "garage_agency": "Garage Agency",
    "client": "Client",
    "service_station": "Service Station",
    "blackhole": "Blackhole",
    "inactive": "Inactive",
    "active": "Active",
    "scrapped": "Scrapped",
    "garage_not_found": "Garage Not Found",
    "garage_already_purchased": "The garage is already purchased by someone. You can only purchase slots of the garage.",
    "garage_not_purchased_before_purchase_slots": "The garage is not yet purchased. You must purchase the garage before purchasing its slots.",
    "garage_not_purchased": "The garage is not yet purchased.",
    "garage_has_slots": "There are additional slots in the garage and they must be sold before the garage can be sold.",
    "garage_has_truck": "There is a truck parked in the garage and they must be relocated before the garage can be sold.",
    "garage_slot_is_base_slot": "The slot to be sold is included in the base package when the garage was purchased. It can only be sold by selling the garage.",
    "garage_slot_has_truck": "There is a truck parked in the garage slot and they must be relocated before the slot can be sold.",
    "modify_company_balance_forbidden": "You are not allowed to manipulate the company's balance.",
    "modify_user_balance_forbidden": "You are not allowed to manipulate other users' balance.",
    "amount_must_be_positive": "Transfer amount must be a positive integer.",
    "from_user_not_found": "Sender User Not Found",
    "to_user_not_found": "Recipent User Not Found",
    "view_balance_forbidden": "You are not allowed to view the user's balance.",
    "view_transaction_history_forbidden": "You are not allowed to view the user's transaction history.",
    "modify_balance_visibility_forbidden": "You are not allowed to modify the visibility of the user's balance.",
    "balance_visibility_already_public": "The user's balance is already public.",
    "balance_visibility_already_private": "The user's balance is already private.",
    "from_to_user_must_not_be_same": "Sender and recipent must not be the same.",
    "cannot_transfer_to_oneself": "You cannot transfer balance to yourself.",
    "merch_not_found": "Merch not found",

    "notification": "Notification",
    "notification_not_found": "Notification Not Found",
    "discord_notification_enabled": "Discord Notification Enabled",
    "new_login": "New login from `{country}` (`{ip}`)",
    "new_login_title": "New Login",
    "ip": "IP",
    "country": "Country",
    "job_submitted": "Job Submitted: `#{logid}`",
    "job_deleted": "Job Deleted: `#{logid}`",
    "earned_bonus_point": "You earned `{bonus_points}` bonus points for delivery `#{logid}` since your rank is `{rankname}`",
    "new_rank": "You have received a new rank: `{rankname}`",
    "new_rank_title": "New Rank",
    "member_accepted": "You have been accepted as a member!\nYour User ID is `{userid}`.",
    "role_updated": "Your roles have been updated:\n{detail}",
    "point_updated": "You have received `{distance}km` and `{bonus_points}` bonus points.",
    "member_resigned": "You have resigned.",
    "member_dismissed": "You have been dismissed.",
    "application_submitted": "{application_type} application submitted.\nApplication ID: `#{applicationid}`",
    "application_submitted_title": "Application Submitted",
    "application_id": "Application ID",
    "application_status_updated": "Application `#{applicationid}` status updated to `{status}`",
    "application_status_updated_title": "Application Status Updated",
    "division": "Division",
    "division_validation_request_submitted": "Division Validation Request for Delivery `#{logid}` submitted.",
    "division_validation_request_submitted_title": "Division Validation Request Submitted",
    "log_id": "Log ID",
    "division_validation_request_status_updated": "Division Validation Request for Delivery `#{logid}` status updated to `{status}`",
    "division_validation_request_status_updated_title": "Division Validation Request Status Updated",
    "event_updated_received_points": "Event `{title}` (Event ID: `{eventid}`) updated: You received `{points}` points.",
    "event_updated_lost_points": "Event `{title}` (Event ID: `{eventid}`) updated: You lost `{points}` points.",
    "event_updated_received_more_points": "Event `{title}` (Event ID: `{eventid}`) updated: You received `{gap}` points. You got `{points}` points from the event in total.",
    "event_updated_lost_more_points": "Event `{title}` (Event ID: `{eventid}`) updated: You lost `{-gap}` points. You still got `{points}` points from the event.",
    "delivery_accepted_by_challenge": "Delivery `#{logid}` accepted by challenge `{title}` (Challenge ID: `{challengeid}`)",
    "delivery_added_to_challenge": "Delivery `#{logid}` added to challenge `{title}` (Challenge ID: `{challengeid}`)",
    "delivery_removed_from_challenge": "Delivery `#{logid}` removed from challenge `{title}` (Challenge ID: `{challengeid}`)",
    "one_time_personal_challenge_completed": "One-time personal challenge `{title}` (Challenge ID: `{challengeid}`) completed: You received `{points}` points.",
    "recurring_challenge_completed_status_added": "1x completed status of recurring personal challenge `{title}` (Challenge ID: `{challengeid}`) added: You received `{points}` points. You got `{total_points}` points from the challenge in total.",
    "company_challenge_completed": "Company challenge `{title}` (Challenge ID: `{challengeid}`) completed: You received `{points}` points.",
    "challenge_uncompleted_increased_delivery_count": "Challenge `{title}` (Challenge ID: `{challengeid}`) is no longer completed due to increased delivery count: You lost `{points}` points.",
    "challenge_completed_decreased_delivery_count": "Challenge `{title}` (Challenge ID: `{challengeid}`) completed due to decreased delivery count: You received `{points}` points.",
    "challenge_uncompleted_increased_distance_sum": "Challenge `{title}` (Challenge ID: `{challengeid}`) is no longer completed due to increased distance sum: You lost `{points}` points.",
    "challenge_completed_decreased_distance_sum": "Challenge `{title}` (Challenge ID: `{challengeid}`) completed due to decreased distance sum: You received `{points}` points.",
    "n_personal_recurring_challenge_uncompelted_increased_delivery_count": "{count}x completed statuses of recurring personal challenge `{title}` (Challenge ID: `{challengeid}`) are lost due to increased delivery count: You lost `{points}` points. You still got `{total_points}` points from the challenge.",
    "one_personal_recurring_challenge_uncompelted_increased_delivery_count": "1x completed status of recurring personal challenge `{title}` (Challenge ID: `{challengeid}`) is removed due to increased delivery count: You lost `{points}` points. You still got `{total_points}` points from the challenge.",
    "n_personal_recurring_challenge_compelted_decreased_delivery_count": "{count}x completed statuses of recurring personal challenge `{title}` (Challenge ID: `{challengeid}`) added due to decreased delivery count: You received `{points}` points. You got `{total_points}` points from the challenge in total.",
    "one_personal_recurring_challenge_compelted_decreased_delivery_count": "1x completed status of recurring personal challenge `{title}` (Challenge ID: `{challengeid}`) added due to decreased delivery count: You received `{points}` points. You got `{total_points}` points from the challenge in total.",
    "personal_onetime_challenge_completed": "One-time personal challenge `{title}` (Challenge ID: `{challengeid}`) completed: You received `{points}` points.",
    "challenge_updated_received_more_points": "Challenge `{title}` (Challenge ID: `{challengeid}`) updated: You received `{points}` points. You got `{total_points}` points from the challenge in total.",
    "challenge_updated_received_points": "Challenge `{title}` (Challenge ID: `{challengeid}`) updated: You received `{points}` points.",
    "challenge_updated_lost_more_points": "Challenge `{title}` (Challenge ID: `{challengeid}`) updated: You lost `{points}` points. You got `{total_points}` points from the challenge in total.",
    "challenge_updated_lost_points": "Challenge `{title}` (Challenge ID: `{challengeid}`) updated: You lost `{points}` points.",
    "challenge_uncompleted_lost_points": "Challenge `{title}` (Challenge ID: `{challengeid}`) is no longer completed: You lost `{points}` points.",
    "one_personal_recurring_challenge_uncompleted": "1x completed status of recurring personal challenge `{title}` (Challenge ID: `{challengeid}`) is removed: You lost `{points}` points.",
    "one_personal_recurring_challenge_uncompleted_still_have_points": "1x completed status of recurring personal challenge `{title}` (Challenge ID: `{challengeid}`) is removed: You lost `{points}` points. You still got `{total_points}` points from the challenge.",
    "economy_transaction_message": "**Message**: {message}",
    "economy_message_for_delivery": "For Delivery `#{logid}`",
    "economy_sent_transaction": "You sent **{amount} {currency_name}** to `{to_user}` (User ID: `{to_userid}`).{message}",
    "economy_received_transaction": "`{from_user}` (User ID: `{from_userid}`) sent **{amount} {currency_name}** to you.{message}",
    "economy_sent_transaction_item": "You transferred ownership of {type} **{name}** to `{to_user}` (User ID: `{to_userid}`).{message}",
    "economy_received_transaction_item": "`{from_user}` (User ID: `{from_userid}`) transferred ownership of {type} **{name}** to you.{message}",

    "system": "System",
    "protected": "Protected",
    "unknown": "Unknown",
    "unknown_user": "Unknown User",
    "discord_api": "Discord API",
    "updated_config": "Updated config",
    "reloaded_config": "Reloaded config",
    "restarted_service": "Restarted service",
    "rejected_tracker_webhook_post_ip": "Rejected {tracker} webhook update from `{ip}` (IP not whitelisted)",
    "rejected_tracker_webhook_post_signature": "Rejected {tracker} webhook update from `{ip}` (Invalid signature)",
    "delivery_blocked_due_to_rules": "Delivery ({tracker} ID: `{trackerid}`) blocked due to rules.\nViolation: `{rule_key}` is `{rule_value}`.",
    "route_already_fetched": "Route is already fetched.",
    "tracker_must_be": "Tracker must be {tracker}.",
    "member_resigned_audit": "Member resigned.",
    "error_removing_discord_role": "Error `{code}` when removing <@&{discord_role}> from <@!{user_discordid}>: `{message}`",
    "error_adding_discord_role": "Error `{code}` when adding <@&{discord_role}> ti <@!{user_discordid}>: `{message}`",
    "discord_register": "User signed up with Discord from `{country}`",
    "discord_login": "User logged in with Discord from `{country}`",
    "steam_register": "User signed up with Steam from `{country}`",
    "steam_login": "User logged in with Steam from `{country}`",
    "password_register": "User signed up with email from `{country}`",
    "password_login": "User logged in with password from `{country}`",
    "mfa_login": "User logged in with MFA from `{country}`",
    "deleted_delivery": "Deleted delivery `#{logid}`",
    "failed_to_add_user_to_tracker_company": "Failed to add `{username}` (User ID: `{userid}`) to {tracker} company.  \nError: {error}",
    "added_user_to_tracker_company": "Added `{username}` (User ID: `{userid}`) to {tracker} company.",
    "failed_remove_user_from_tracker_company": "Failed to remove `{username}` (User ID: `{userid}`) from {tracker} company.  \nError: {error}",
    "removed_user_from_tracker_company": "Removed `{username}` (User ID: `{userid}`) from {tracker} company.",
    "updated_global_note": "Update global note of `{username}` (UID: `{uid}`) to `{note}`.",
    "updated_user_roles": "Updated roles of `{username}` (User ID: `{userid}`)",
    "role": "Role",
    "updated_user_points": "Updated points of `{username}` (User ID: `{userid}`):\n  Distance: `{distance}km`\n  Bonus Points: `{bonus_points}`",
    "dismissed_member": "Dismissed `{username}` (UID: `{uid}`)",
    "accepted_user_as_member": "Accepted `{username}` (User ID: `{userid}` | UID: `{uid}`) as member.",
    "updated_connections": "Updated account connections of `{username}` (UID: `{uid}`)",
    "deleted_connections": "Deleted account connections of `{username}` (UID: `{uid}`)",
    "forever": "forever",
    "until": "until `{datetime}` UTC",
    "banned_user": "Banned `{username}` (UID: `{uid}`) {expire}.",
    "unbanned_user": "Unbanned `{username}` (UID: `{uid}`)",
    "deleted_user": "Deleted user: `{username}` (UID: `{uid}`)",
    "deleted_user_pending": "Received user deletion request: `{username}` (UID: `{uid}`)\nUser will be deleted after a cooldown period of 14 days.",
    "disabled_mfa": "Disabled MFA for `{username}` (UID: `{uid}`)",
    "created_announcement": "Created announcement `#{id}`",
    "updated_announcement": "Updated announcement `#{id}`",
    "deleted_announcement": "Deleted announcement `#{id}`",
    "updated_application_positions": "Updated application positions to `{positions}`.",
    "updated_application_status": "Updated application `#{id}` status to `{status}`",
    "deleted_application": "Deleted application `#{id}`",
    "created_challenge": "Created challenge `#{id}`",
    "updated_challenge": "Updated challenge `#{id}`",
    "deleted_challenge": "Deleted challenge `#{id}`",
    "added_delivery_to_challenge": "Added delivery `#{logid}` to challenge `#{id}`",
    "removed_delivery_from_challenge": "Removed delivery `#{logid}` from challenge `#{id}`",
    "updated_division_validation": "Updated division validation status of delivery `#{logid}` to `{status}`",
    "created_downloads": "Created downloadable item `#{id}`",
    "updated_downloads": "Updated downloadable item `#{id}`",
    "deleted_downloads": "Deleted downloadable item `#{id}`",
    "created_event": "Created event `#{id}`",
    "updated_event": "Updated event `#{id}`",
    "deleted_event": "Deleted event `#{id}`",
    "updated_event_attendees": "Updated event `#{id}` attendees",
    "added_attendees": "New attendees - Given `{points}` points to",
    "removed_attendees": "Removed attendees - Removed `{points}` points from",
    "added_event_points": "Updated points - Added `{points}` points to",
    "removed_event_points": "Updated points - Removed `{points}` points from",
    "no_changes_made": "No changes made.",
    "updated_poll": "Updated poll `#{id}`",
    "deleted_poll": "Deleted poll `#{id}`",
    "purchased_truck": "Purchased truck `{name}` (ID: `{id}`) for `{username}` (User ID: `{userid}`).",
    "transferred_truck": "Transferred truck `#{id}` to `{username}` (User ID: `{userid}`).",
    "reassigned_truck": "Reassigned truck `#{id}` to `{username}` (User ID: `{userid}`).",
    "removed_truck_assignee": "Removed assignee of truck `#{id}`.",
    "unknown_garage": "Unknown garage",
    "relocated_truck": "Relocated truck `#{id}` to `{garage}` (ID: `{garageid}`) slot `#{slotid}`.",
    "transferred_garage": "Transferred garage `{garage}` (ID: `{id}`) to `{username}` (User ID: `{userid}`).",
    "transferred_slot": "Transferred garage slot `#{id}` to `{username}` (User ID: `{userid}`).",
    "sold_garage": "Sold garage `{garage}` (ID: `{id}`) which is owned by `{username}` (User ID: `{userid}`).",
    "sold_slot": "Sold slot `#{id}` which is owned by `{username}` (User ID: `{userid}`)."
}
