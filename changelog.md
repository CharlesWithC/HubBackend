# Changelog

## v2.10.6

1. Added `attended` attribute in **GET** `/events/list`

## v2.10.5

1. Fixed email encoding issue with certain mail clients
2. Optimized delivery export feature for fast full-database export
   - Also, split `tollgate`, `ferry`, `train`, `total` expense into separate columns
3. Switched to `zstd` for data compression and decompression
4. Switched to `cysimdjson` for json parsing in dlog export for 10x faster performance

## v2.10.4

1. Improved Discord API error handling
2. Added support to German and Spanish banner rendering
3. Updated Portuguese string table

## v2.10.3

1. Fixed issues with database connection pool management
2. Added multi-statement SQL query block
3. Added SQL comment and DROP statement block
4. Added error in audit log on Discord API 400 Response

## v2.10.2

1. Minor bug fixes
2. Adjusted rate limit
3. Added support to centralized database connection pool
   - Use single connection pool for all hubs running under a single service
   - Enable this feature by toggling on the option `--use-master-db-pool`
   - `--master-db-host`, `--master-db-user`, `--master-db-password`, `--master-db-pool-size` must be provided as well
4. Added `dlog_meta` table for **GET** `/dlog/list` to reduce database delay
5. Added automatic discord role removal on member leave
6. Added support to modifying join timestamp
7. Fixed issue of cache not being refreshed when it is constantly being hit

## v2.10.1

1. Respect launch params when setting host, port and workers
2. Switched to use https protocol for steam api requests
3. Added `last_seen_before` param to **GET** `/member/list`
4. Moved **GET** `/divisions` to **GET** `/divisions/statistics`
5. Added **GET** `/divisions/{divisionid}/activity` for per-user statistics

## v2.10.0

1. Added task plugin
2. Added cancel user deletion request audit log
3. Fixed boolean data in dlog export

## v2.9.5

1. Improved banner generator:
   - Ability to choose whether to show division or rank as front row in the right side.
   - Accept custom background image defined by `banner_background_url` in config.
   - Accept custom background opacity defined by `banner_background_opacity` in config.

2. Added daily bonus reminder notification:
   - User may choose any time in the day to receive the notification.
   - Added **PATCH** `/member/bonus/notification/settings` to update notification settings.
   - Added **GET** `/member/bonus/notification/settings` to fetch notification settings.

3. Added support to modifying request object through middleware
   - Modified standard return value of `request` middleware: Originally only an optional `response` is returned. Currently either `None` or a tuple of `(request, response)` has to be returned. If `response` is not `None`, then the `response` will be returned directly. Otherwise, the request will be processed normally.

4. Added `discord_request` middleware to manipulate data sent to Discord
   - The  `method`, `url` and `data` in requests will be passed to `discord_message` middleware, and the middleware must return a valid `data` which will be sent to Discord.
   - If there are multiple middlewares present, the `data` will be updated by earlier ones in the list, and the updated data will be passed to later ones.
   - The middleware function must be synchronous and asynchronous functions will be not executed.

## v2.9.4

1. Fixed data inconsistency due to outdated transactions, see details below:  
   Since we use connection pools, connections are not newly created and re-used. Thus, there may be a transaction opened previously when a connection is acquired. Due to database transaction isolation level set to `READ REPEATABLE`, updates made after the transaction was opened are not reflected in the transaction. As a solution, we would run `ROLLBACK` and `BEGIN` on all newly acquired connections, to ensure that the previous transaction is closed and a new transaction is started.  
   Credit: Thanks to @dowmeister for helping with this issue.
2. Improved sub-application startup and shutdown event (aka, lifespan) handling, see details below:  
   Due to FastAPI/Starlette not supporting lifespan events in sub-applications, we previously called startup event with middleware when the first request is sent in, which potentially leads to database connection timeout due to lack of available connections in connection pool. To solve this issue, we are now calling startup event for sub-applications one by one from main application lifespan event. In addition, the function to close database connection pool on shutdown is added, so the database could be shutdown more gracefully.
3. Added retries and supported optional increased timeout for database connection acquisition, see details below:
   To further reduce the possibility of `Timeout` errors, we added retries on connection acquisition. Also, considering that we attempt to acquire a number of connections on startup and this may lead to lack of available connections, the timeout on connection acquisition for functions executed in startup event is increased to 10 seconds.
4. Added `division.status` in **GET** `/dlog/list`, made division status public to all users in **GET** `/dlog/{logid}/division`
5. Added `dlog` in **GET** `/challenge/{challengeid}` for a list of dlog ids

## v2.9.3

Updated dependencies:

- fastapi 0.100.0 => 0.110.2
- uvicorn 0.23.1 => 0.29.0
- aiohttp 3.8.5 => 3.9.5
- aiosmtplib 2.0.2 => 3.0.1
- bcrypt 4.0.1 => 4.1.2
- pillow 10.0.0 => 10.3.0
- python-dateutil 2.8.2 => 2.9.0
- python-multipart 0.0.6 => 0.0.9
- psutil 5.9.5 => 5.9.8
- pydantic 2.1.1 => 2.7.0

## v2.9.2

1. Added `distance_note` and `bonus_note` to **PATCH** `/member/points`  
   Both `note` would be stored in `database`, `distance_note` in JSON in `data` column for `dlog` table and `bonus_note` in `note` column of `bonus_point` table  
   Both `note` would also be stored in audit log
   Additionally, `staff_userid` would be stored along with `distance_note` in `data` column for `dlog` table
2. Updated **GET** `/member/bonus/history`  
   Added `type` param which could be `daily` (default) or `all`.  
   When `type = daily`, all bonus history would be returned, including manually added ones and daily/distance bonus.
3. Updated **GET** `/dlog/list`  
   Added `manual: bool` param (default: `False`) which controls whether manually added distance is returned or tracked distance is returned.
   When `manual = true`, all manually added distance, along with the staff user and note would be returned.
4. Fixed wrong key ordering in user object due to redis caching

## v2.9.1

1. Added audit log category attribute  
   Available categories: `announcement`, `application`, `auth`, `challenge`, `division`, `dlog`, `downloads`, `economy`, `event`, `member`, `poll`, `system`, `tracker`, `user`  
   Additionally, `legacy` category is used for all audit log generated before `v2.9.1` ; `discord` category is used for Discord-related logs.  
2. Added detailed challenge completion record  
   NOTE: `completed` object was changed to `record` in **GET** `/challenge/{challengeid}`; `completed` (count) attribute was changed to `completed_user_count` in **GET** `/challenge/list`.
3. Added driver role validation when accepting jobs from webhook
4. Fixed error when webhook signature does not exist
5. Fixed error when adding a driver from Trucky webhook when the user exists in the database but does not have driver role

## v2.9.0

In this update, cache and other temporary data are moved to (in-memory) redis, which prolonged cache life, reduced database operations and allowed expiry refresh when the same resource is accessed. Also, it supported making updates to relevant data directly rather than waiting for cache to expire.  

All cache are set to expire after 60 seconds when the same resource is not accessed again, except `uactivity`, `alluserids` and `nlb` that expires 60 seconds after creation regardless of how many times it is accessed.

1. Switched `app.state.cache_session(_extended)` to redis `auth:{authorization_key}`.
2. Switched `app.state.cache_language/timezone/privacy/note` to redis `ulang:{uid}` / `utz:{uid}` / `uprivacy:{uid}` / `unote:{from_uid}/{to_uid}`
3. Added redis `umap:userid/discordid={id}` to link `userid` and `discordid` to `uid`
4. Switched `app.state.cache_userinfo/activity` to redis `uinfo:{uid}` / `uactivity:{uid}`
5. Simplified ratelimit handling by switching to redis, and removed the necessity of database operations
6. Added delay on request handling when multiple requests on the same route are received at the same time
7. Switched `app.state.cache_statistics` to redis `stats:{id}` and improved query algorithm
8. Switched `app.state.cache_leaderboard` and `cache_nleaderboard` to redis `lb` and `nlb` and improved query algorithm
9. Switched `app.state.cache_all_users` to redis `alluserids` and simplified cache expiry code
10. Switched `app.state.running_export` to redis `running_export` thus limited active dlog export process to one in all processes
11. Switched `app.state.session_errs` to redis `session_errs` thus prevented duplicate error webhook being sent (by multiple processes)
12. Switched from mysql database to redis for multiprocess handling
13. Added traceback handler for event and poll backgroud tasks

## v2.8.10

1. Improved param validation and added error response when `page`, `page_size`, `order`, `order_by` is invalid
2. Added support to custom tracker
   - `tracker.type`: `custom` | URL: `/custom-tracker/update`
   - `api_token` will not be used
   - Webhook signature header's key must be `signature`
   - Webhook data must follow TrackSim's format, otherwise may lead to `Internal Server Error`
   - `route` object may be included in `data.object`, which must follow the format of an array of objects containing `x`, `z`, `time` (`[{x: float, z: float, time: int}, {x: float, z: float, time: int}, ...]`)
   - `warp` value may be included in `data.object`, which must be an integer or a decimal
3. Added delayed cache clear to ensure async data consistency

## v2.8.9

1. Fixed Internal Server Error caused by email validating (`NoneType`)  
   - This includes: accepting a user / submitting an application when the user's email is not set
2. Fixed invalid email (`"None"`) being stored in database  
3. Made **PATCH** `/user/profile` to return updated user info as response (which also clears user info cache)
4. Added notification on ownership transfer for economy garage, garage slot, truck and merch

**Note**: This update will attempt to change all `"None"` (string) email in database to `NULL` (NULL)

## v2.8.8

1. Fixed issue updating multiple account connections at the same time
2. Renamed `config.smtp_passwd` to `config.smtp_password`
3. Renamed confusing `query` param key to more specific keys like (`name`, `reason`)
4. Added `?name` query param to **GET** `/user/ban/list`
5. Added add/remove driver from tracker company when staff update driver's steam connection
6. Improved `?order_by` handling
   - Improved second key
   - Renamed `user_id` to `userid` in **GET** `/member/list`
   - Added `timestamp` to **GET** `/notification/list`
   - Added `steamid`, `truckersmpid` to **GET** `/member/list`
   - Added `userid`, `timestamp` to **GET** `/dlog/list`
   - Removed `type`, `status` from **GET** `/applications/list`
   - Added `txid` to **GET** `/economy/balance/{userid}/transactions/list`
   - Added `garageid` to **GET** `/economy/garages/list`
   - Renamed `timestamp` to `create_timestamp` in **GET** `/events/list`
   - Hint: `timestamp` mostly refers to `timestamp` of resource creation
7. Added `config.divisions[].staff_role_ids` to limit staff access to each type of divisions
8. Added `config.divisions[].message|channel_id|webhook_url` for per-division discord notification
9. Rename `config.application_types[].role_change|allow_multiple` to `discord_role_change` and `allow_multiple_pending`
10. Added `X-Database-Response-Time` when `performance-header` is enabled
11. Added Dutch Translation

## v2.8.7

1. Reordered config keys
2. Fixed error loading languages files with `utf-8` encoding
3. Fixed error handling Trucky job with `refuel` event
4. Updated error message for `tracker.{api_token|webhook_secret}` to `trackers[{index}].{api_token|webhook_secret}`
5. Updated `ban_history` logic to create history record once ban is placed
6. Renamed values of `config.delivery_rules.action` for easier understanding:
   - `bypass` -> `keep_job`
   - `drop` -> `drop_data`
   - `block` -> `block_job`
7. Added auto-fill for missing attributes in `config.delivery_rules`
8. Removed application position handling - this should be done by frontend
9. Added country/region handling for local network
10. Renamed permissions
    - NOTE: Position-based permissions Human Resources Manager (`hrm`) and Human Resources (`hr`) have been removed. Roles with these permissions will be granted relevant function-based permissions automatically. This grant will be done in all future releases as long as `hrm` and `hr` permissions still exist in `config.perms`.

| Old Permission Name   | New Permission Name       |
| :-------------------- | :------------------------ |
| admin                 | administrator             |
| config                | update_config             |
| restart               | restart_service           |
| add_member            | accept_members            |
| dismiss_member        | dismiss_members           |
| update_member_roles   | update_roles              |
| update_member_points  | update_points             |
| update_user_connections | update_connections       |
| disable_user_mfa      | disable_mfa               |
| manage_profile        | manage_profiles           |
| get_sensitive_profile | view_sensitive_profile    |
| get_privacy_protected_data | view_privacy_protected_data |
| get_user_global_note  | view_global_note          |
| update_user_global_note | update_global_note      |
| get_pending_user_list | view_external_user_list   |
| ban_user              | ban_users                 |
| delete_user           | delete_users              |
| import_dlog           | import_dlogs              |
| delete_dlog           | delete_dlogs              |
| audit                 | view_audit_log            |
| announcement          | manage_announcements      |
| application           | manage_applications       |
| delete_application    | delete_applications       |
| challenge             | manage_challenges         |
| economy_manager       | manage_economy            |
| balance_manager       | manage_economy_balance    |
| truck_manager         | manage_economy_truck      |
| garage_manager        | manage_economy_garage     |
| merch_manager         | manage_economy_merch      |
| division              | manage_divisions          |
| downloads             | manage_downloads          |
| event                 | manage_events             |
| poll                  | manage_polls              |

## v2.8.6

1. Fixed minor issue with dlog statistics
2. Added global MFA requirement to **POST** `/user/mfa/disable`
3. Added member role sync-to-discord feature
4. Improved string table
5. Improved config format

## v2.8.5

1. Added **POST** `/status/database/restart` to manually restart database pool
   - There is no access control for this endpoint because access control will not work when database is down.
   - Database must be unavailable when requesting database pool restart.
   - Automatic restart should usually work and this function is only a last solution.
2. Fixed issues related to `member role` handling
   - Updated **GET** `/member/banner` to use `order id` to order roles rather than using `role id`
   - Fixed **PATCH** `/member/roles` error when adding/removing an unknown role
3. Fixed Trucky job format conversion issues
   - Fixed error handling new jobs when `real_driven_distance_km = None`
4. Improved economy plugin
   - Fixed **GET** `/economy` leading to broken garages and trucks list
   - Fixed `GetTruckInfo` error when `vehicleid = None`
   - Fixed 422 errors when calling truck-related endpoints
   - Fixed incorrect damage data being used (`total_damage`, should be `current_damage`)
   - Fixed `self` being used as default owner on **POST** `/truck/transfer`
   - Fixed purchasing merch does not correctly deduct balance
   - Added `visibility` attribute to result of **GET** `/economy/balance`
   - Added the `wear_ratio` calculation
   - Added **PATCH** `/balance/{userid}` to update balance without making transaction
   - Limited transaction economy date range to 90 days
   - Limited job income to `4294967296`
   - Included all types in transaction list & export

## v2.8.4

1. Fixed Trucky job format conversion issues  
2. Added `?bypass_tracker_check=true|false` to `/trucky/import`  
3. Fixed error loading poll list  
4. Added `voted=true|false` to `poll` and `poll.choices` in `/poll/lists` and `/poll/{pollid}`  
5. Improved Discord profile handling: try `global_name` before `username`  
6. Integrated Trucky `realistic_settings` with `delivery_rules` (`enabled_realistic_settings`) and `challenge` plugin (`required_realistic_settings` in job requirements)  
7. Fixed incorrect damage when tracker is Trucky  

## v2.8.3

1. Minor improvements on string table and `apidoc.json`  
2. Deduplicated roles and event attendees on update  
3. Prevented disabling password login when there is no other login method  
4. Fixed detailed statistics unable to continue automatically when a dlog is deleted  
5. Added MFA verification on user deletion (self-operation)  
6. Added audit log for updating global note  
7. Removed authorization requirement when using email confirmation link  
8. Added German translation  

## v2.8.2

1. Fixed Trucky webhook handling issues  
2. Fixed update-connection failure when the provided connections are unchanged  
3. Fixed incorrect `role_history` data being returned  
4. Updated update-connection logic
   - Non-member users with conflicting connections will no longer be deleted automatically.
   - It is required to delete connection-conflicting users manually to proceed.  
5. Updated delete-connection logic
   - Steam & TruckersMP connection will no longer be deleted by default.
   - It is no longer needed to dismiss a member before deleting connections.
   - It is allowed to delete a specific connection by providing it in `path`.  
   - The endpoint has been re-routed from **DELETE** `/user/{uid}/connections` to **DELETE** `/user/{uid}/connections/{connection}`. `{connection}` is a string whose value is among `email`, `discordid`, `steamid`, `truckersmpid`.
6. Added `?email` query param to **GET** `/user/profile`  
7. Added support to TrackSim-Trucky Hybrid Tracker  
   - Definition of "default tracker": `config.tracker` if config has not been updated to the new format, or `config.tracker[0].type` if config has been updated to the new format.
   - The upgrader will set all user's tracker to the default tracker. The format of `config.tracker` will also be updated, which is a list containing multiple dictionaries, whose format looks like `{"type": str, "company_id": int, "api_token": str, "webhook_secret": str, "ip_whitelist": list}`.
   - On **POST** `/user/{uid}/accept`, `tracker` should be provided to set the tracker the user will be using. Otherwise, the default tracker will be used.
   - A new endpoint **POST** `/user/tracker/switch` has been created to allow user or staff to change the user's tracker. `update_member_roles` permission is required to update the tracker for another user.
   - `tracker` attribute has been added to `user` object.
   - When a driver is to be added to the tracker company, the driver will be added to all tracker companies no matter which tracker they choose to use. This is to prevent additional work to be done when the driver changes the tracker in the future.
   - When a driver submits a job, `tracker_in_use` will be checked to ensure that the data is coming from the correct tracker to prevent duplicate jobs.
   - Theoretically, there is no hard limit on the number of trackers, even if they are of the same `type`. But adding too many trackers may lead to downgraded performance on relevant functions, including adding/removing drivers to/from the tracker company. Though measures have been taken to prevent duplicate jobs from the same tracker being logged when multiple webhooks are sent at the same time (there is lag on database and multiple webhooks coming in at the same time may cause inability to detect duplicate jobs), we cannot promise that no duplicate jobs from the same tracker will be logged.
   - Hence, considering that we currently support TrackSim and Trucky as tracker, it's recommended to configure up to `2` trackers, one of TrackSim and one of Trucky.

## v2.8.1

1. Added **POST** `/trucky/import/{jobid}` to import jobs from Trucky  
2. Added `user_joined_company` Trucky webhook event listening  
3. Fixed the issue that empty email may lead to wrong ban check  

## v2.8.0

1. Removed `company_driver.detached` tracksim event listening  
2. Added "update discord email" when user reconnects discord account and email is not connected  
3. Added `config.discord_guild_message_replace_rules` for manipulating discord message content before sending  
    Config format: `{regex_match_rule_1(str): regex_replace_rule_1(str), ..., regex_match_rule_n(str): regex_replace_rule_n(str)}`
4. Added distance-based division points  
    Config format: `{"id": int, "name": str, "role_id": int, "points": {"mode": str("static"|"ratio"), "value": int|float}}`  
    When `mode` is `static`, each validated division delivery gets static points.  
    When `mode` is `ratio`, each validated division delivery gets `distance * value` points.  
    **Note**: Points of previously validated division deliveries will be updated when config is updated.  
5. Added support to multiple rankings  
    **Hint**: This function mainly focuses on providing multiple rank roles.  
    Config format: `[{"id": int, "name": str, "default": bool, "point_types": list: ["distance", "challenge", "division", "event", "bonus"], "details": ...original_ranks}]`  
    At least one item must have `default = true`, otherwise the first one will be considered `default`. The `default` ranking will be used for `daily_bonus` and `distance_bonus`. Specific `rank_type_id` will only be considered when user is requesting discord role for a specific rank type.  
    `point_types` must be a list with `str` items selected from `["distance", "challenge", "division", "event", "bonus"]`.  
    `details` have the same format has the original `config.ranks`.  
6. Added Trucky Integration  
    **Hint**: Data will be converted to TrackSim style. Data provided by TrackSim but not Trucky will become `None/null`. Patial data (`timezone`, `warp`) provided by Trucky but not TrackSim will be added.  
    Removed features: xp-related attributes for delivery_rules (`max_xp`) and challenges (`minimum|maximum_xp`)  
    Added features: warp-related attributes for delivery_rules (`max_warp`) and challenges (`minimum|maximum_warp`)  

## v2.7.15
  
1. Enforced `deepcopy` for most large dicts to prevent constants being changed  
2. Renamed `config.delivery_post_gifs` to `delivery_webhook_image_urls` and added config-level url validation  

## v2.7.14
  
1. *\[BannerGen\]* Blocked large logo and avatar (larger than 10MB or 3400x3400)  
2. *\[BannerGen\]* Added logo and avatar resizing before processing to prevent memory outage  

## v2.7.13
  
1. Added `minimum_seconds_spent`, `maximum_seconds_spent`, `maximum_distance`, `minimum_detour_percentage`, `maximum_detour_percentage`, `minimum_adblue`, `maximum_adblue`, `minimum_fuel`, `market`, `game`, `truck_id`, `truck_plate_country_id`, `minimum_truck_wheel`, `maximum_truck_wheel`, `maximum_cargo_mass`, `minimum_cargo_damage`, `minimum_offence`, `minimum_xp`, `maximum_xp`, `minimum_train`, `maximum_train`, `minimum_ferry`, `maximum_ferry`, `minimum_teleport`, `maximum_teleport`, `minimum_tollgate`, `maximum_tollgate`, `minimum_toll_paid`, `maximum_toll_paid`, `minimum_collision`, `maximum_collision` to challenge job requirements  
2. Fixed the bug that user with empty ("") email cannot be correctly banned  
3. Added `config.delivery_rules.max_xp` to limit the maximum xp earned  
4. Added `--memory-threshold` (in MB) to reject new requests when memory is insufficient  
5. Added `--banner-service-url` to customize banner service URL  

## v2.7.12
  
1. Added customizable host, port, workers for banner generator  
2. Improved banner generator to delete unused variables timely  
3. Limited export function to export a maximum range of 90 days of data  
    As a solution to prevent database outage  
    Rate limit is reduced to 3req/150sec

## v2.7.11
  
1. Removed secret data from **GET** `/application/types`  
2. Removed `config.application_types[].discord_role_id` that only supports adding roles  
3. Added `config.application_types[].role_change` to support addition/removal of multiple roles  
4. Limited additional authorization check to specific routes that allows non-authorized users  
5. Improved `arequests` to raise error after 3 retries (otherwise it will return `None`)  
6. Updated maximum value of timestamp-related data to `9223372036854775807`  
7. Renamed `application_type`, `update_timestamp`, `last_update_staff` in request and response to `type`, `respond_timestamp`, `last_respond_staff`  
8. Renamed `?created_by` in **GET** `/applications/list` to `?submitted_by`  
9. Added `?submitted_after|before`, `?responded_after|before` and `?responded_by` to **GET** `/applications/list`  
10. Added `?order_by` to **GET** `/applications/list` (supported values: `applicationid`, `type`, `status`, `submit_timestamp`, `respond_timestamp`, `applicant_uid`, `respond_staff_userid`)  
11. Renamed `?after|before` to `?meetup_after|before`, added `?departure_after|before`, `?min|max_vote|attendee` to **GET** `/events/list`  
12. Renamed `?after|before` to `?created_after|before` for **GET** `/announcements/list`, `/polls/list`  
13. Added `?created_after|before` to **GET** `/challenges/list`, `/downloads/list`, `/events/list`  
14. Added `?end_after|before` to **GET** `/polls/list`  
15. Added `?min|max_click` to **GET** `/downloads/list`  
16. Updated application plugin logic: Setting `status` to `pending` will not reset `respond_timestamp`  
17. Moved route **PATCH** `/applications/{applicationid}` to **POST** `/applications/{applicationid}/message`  
18. Added **PUT/DELETE** `/tracksim/driver/{userid}` route to add/remove driver from TrackSim company  

## v2.7.10
  
1. Fixed incorrect info in [openapi.json](./openapi.json)  
2. Fixed 500 error in challenge plugin when invalid `job_requirements` is provided  
3. Added `config.event_upcoming_forwarding` for forwarding upcoming events  
4. Added detailed reason of blocking dlog  
5. Included basic user info in application discord embed when the full message is too long  
6. Added `seconds_ahead` to `config.event_upcoming_forwarding` (3600 by default, maximum 86400 * 7)  
7. Added `config.challenge_completed_forwarding`  

## v2.7.9
  
1. Renamed `announcement_type` to `type`  
2. Renamed `challenge_type` to `type`  
3. Removed `?after|before` query from **GET** `/challenges/list`  
4. Added `?start_after|before` and `?end_after|before` to **GET** `/challenges/list`  
5. Removed `?roles` query from **GET** `/members/list`  
6. Added `?include_roles|exclude_roles` to **GET** `/members/list`  
7. Added `creator` field to event and challenge objects  
8. Fixed legacy functions using `role id` to order roles  

## v2.7.8
  
1. Added handling of `autoPark` field on dlog export  
    This should be a TrackSim issue  
2. Added retries on `arequests`  
3. Added `?voted_by`, `?is_private` to **GET** `/events/list`  
    Also made `?attended_by` and `?voted_by` only usable by members  
4. Added `voted` field to event objects in the response of **GET** `/events/list`, `/event/{eventid}`  
5. Added `?is_private` to **GET** `/announcements/list`  
6. Added advanced forward-to-discord function to announcement, challenge, downloads, event and poll plugin  

## v2.7.7
  
Added user note (private / global)  
    To remove the note, provide an empty string on `note` field when updating it  

## v2.7.6
  
1. Improved discord embed handler  
    Support any fields, so no update is needed to catch up with the changing discord  
    Support more variables, including `{avatar}` and `{staff_*}`  
    Support multiple embeds in one message  
2. Improved application restrictions with the following config fields  
```{"required_connections": [], "required_member_state": -1, "required_either_user_role_ids": [], "required_all_user_role_ids": [], "prohibited_either_user_role_ids": [], "prohibited_all_user_role_ids": [], "cooldown_hours": 2, "allow_multiple": False}```  
    `require_member_state` = -1: either | 0: not member | 1: is member  
    \*_either_user_role_ids: include either of the roles  
    \*_all_user_role_ids: include all of the roles  

## v2.7.5
  
1. Allowed external plugin to return response  
2. Fixed `v2_7_2` upgrader error when there is no data in `event` table  
3. Removed `percentage` from `config.ranks[].daily_bonus.streak_type` to prevent excessive bonus  
4. Renamed `config.ranks[].bonus` to `distance_bonus`  
5. Disabled TrackSim webhook signature validation when webhook secret is not configured  
6. Added `?after|before` to **GET** `/dlog/statistics/details`  
    Rate limit: 3req/10sec (only applies to requests with time-range query)  
7. Added `?attended_by` to **GET** `/events/list`  
8. Renamed `?creator_userid` to `?created_by` for **GET** `/downloads/list`, `/polls/list`  
9. Renamed `?userid` to `?completed_by` for **GET** `/challenges/list`, `/challenges/{challengeid}`  
10. Added `?created_by` to **GET** `/announcements/list`, `/applications/list`, `/challenges/list`, `/events/list`  
11. Added `?requested_by` to **GET** `/divisions/list/pending`  
12. Added `email`, `account_connections`, `activity`, `public_profile` privacy options  
    Certain staff could always surpass privacy options and get user info  
13. Added **PATCH** `/user/activity` and `config.use_custom_activity`  
    When `use_custom_activity` is `false`, then **PATCH** `/user/activity` will be disabled and activity will be automatically updated when the user does certain API operations. When `use_custom_activity` is `true`, activity will not be automatically updated and user must use **PATCH** `/user/activity` to update the activity, but `last_seen` is always automatically updated  

## v2.7.4
  
1. Fixed update member points audit log  
2. Added detailed description to specific errors  

## v2.7.3
  
1. Fixed invalid table creation scheme of `announcement` and `downloads`  
2. Removed exception type validation from database error judgement  
    Only `config.mysql_err_keywords` will be considered  
3. Fixed `Internal Server Error` being returned for recorded database errors  
4. Added traceback logging for all recorded errors  
    It won't forward the error to Discord webhook when the error is recorded  
    This would enable connection pool restarting  
5. Fixed `500` error on **POST** `/member/bonus/claim` when `config.ranks[].daily_bonus = null`  
    It will now return `404` in such cases  
6. Improved config validator to handle data of wrong types  
7. Added `?sync_to_truckersmp` to **PATCH** `/user/profile`  
8. Added (creation) `timestamp` to `challenge` and `event`  
9. Renamed `config.application_types[].staff_role_id` to `staff_role_ids`  
10. Added `config.announcement_types[]`  
```{"id": int, "name": str, "staff_role_ids": list}```  
**Note** `announcement_type` in response has been converted from `int` to `dict` like `{"id": int, "name": str}`  

## v2.7.2
  
1. Improved value size limit handling  
2. Fixed inappropriate default query value  
3. Added `?after` and `?before` to announcement and poll listing  
4. Added `order_id` and `is_pinned` to event  
5. Improved flexibility of event listing - Added `?order_by`, `?order`, `?before`, `?after_eventid`  
**Note** Expired events will no longer be attached to end of list, alter `?after` to get both active and expired events.  

## v2.7.1
  
1. Minor bug fixes and improvements  
2. Added `algo` to `config.ranks[].daily_bonus.streak_type` - A generic algorithm making the growth rate of the reward decreases as streak increases, solving the issue of `percentage` that leads to ultra high reward when streak is high.  
When `streak_type` is `algo`, there's a `algo_offset` property. It must be a positive number. The smaller it is, the higher the growth rate is when streak is small. Also, it's recommended to set `streak_value` around 1, the larger it is, the higher the growth rate is.  

## v2.7.0
  
1. Added poll plugin  
2. Improved multiprocess handling  
3. Renamed `tracker` plugin to `route`  

## v2.6.3
  
1. Added user role history  
2. Added user ban history  
3. Added `config.ranks[].daily_bonus` and `bonus` notification type  

## v2.6.2
  
1. Added `order_id` and `is_pinned` to announcement, challenge  
2. Removed "forward to Discord" function in announcement  
3. Added `is_pinned` and `timestamp` to downloads  
4. Improved announcement, challenge, downloads, event PATCHing to autofill unprovided fields  
5. Improved announcement, downloads list ordering and filtering  
6. Renamed `event` notification to `upcoming_event`  
7. Added `new_announcement`, `new_challenge`, `new_downloads`, `new_event` notifications  

## v2.6.1
  
1. Fixed `/user/profile` returning incorrect `ban` data  
2. Added `config.privacy` check to **GET** `/dlog/statistics/details`  
3. Added `Authorization` header check to middleware if the header exists  
4. Added `get_sensitive_profile` permission to access user `email` and `mfa`  
5. Added `config.perms` validator to ensure default permissions are included  
6. Improved external plugin handling:  
i) Protected config will be included in the config when calling `init`  
ii) Added `external_middleware` with four types (`startup`, `request`, `response_ok`, `response_fail`). See [README.md](./README.md) for more.  
7. Removed `config.hcaptcha_secret`, added `config.captcha` with `provider` and `secret` property, `provider` supports `cloudflare` and `hcaptcha`.  
**Note** `h-captcha-response` in JSON data has been renamed to `captcha-response`.  

## v2.6.0
  
1. Fixed inaccurate data of **GET** `/dlog/statistics/chart|summary`  
2. Separated `ETS2/ATS` data of **GET** `/dlog/statistics/chart`  
3. Added `?joined_after|before` to **GET** `/user/list`, `/member/list`  
4. Converted `delivery_log_channel_id`, `webhook_division(_message)`, `webhook_audit` to `hook_delivery_log`, `hook_division`, `hook_audit_log` to support both `webhook_url` and `channel_id`  
5. Renamed `config.application_types[].webhook` to `webhook_url`, added `channel_id`  
6. Increased `channel_id` priority in `AutoMessage`, which will try using `channel_id` before using `webhook_url` if set  
7. Added queue for most Discord API calls to handle 429s  
8. Improved notification DM rate limit handler  
9. **Added `dlog_stats` building and GET `/dlog/statistics/details`**  
10. Added `config.ranks[].bonus` for bonus points when submitting a job after driver reaches a rank  
11. Converted partial `INT` columns in `economy_*` TABLE to `BIGINT`  
12. Added `--disable-upgrader` cli switch to prevent running upgrader  

## v2.5.11
  
1. Added `?after` to **GET** `/audit/list`  
2. Added `?after_logid` to **GET** `/dlog/list`  
3. Added `?after_userid`, `?min_point`/`?max_point` to **GET** `/dlog/leaderboard`  
4. Added `?after_userid` to **GET** `/member/list`  
5. Added `?after_uid` to **GET** `/user/list`, `/user/ban/list`  
6. Added `?after_notificationid` to **GET** `/user/notification/list`  
7. Added `?after_announcementid` to **GET** `/announcements/list`  
\* Note: `?order_by` has been removed from the above endpoint  
8. Added `?after_applicationid` to **GET** `/applications/list`  
9. Added `?after_challengeid` to **GET** `/challenges/list`  
10. Added `?after_logid`, `?order`/`?order_by=logid|user|request_timestamp` to **GET** `/divisions/list/pending`  
11. Added `?after_downloadsid` to **GET** `/downloads/list`  
12. Renamed `?first_event_after` to `?after` for **GET** `/events/list`  
13. Added `?after_userid` to **GET** `/economy/balance/leaderboard`  
14. Added `?after_garageid` to **GET** `/economy/garages/list`  
15. Added `?after_slotid` to **GET** `/economy/garages/slots/list`  
16. Added `?after_itemid` to **GET** `/economy/merch/list`  
17. Added `?after_vehicleid` to **GET** `/economy/trucks/list`  
18. Added `?after_txid`/`?after`/`?before` to **GET** `/economy/trucks/{vehicleid}/{operation}/history`  
19. Added **DELETE** `/user/notification` to delete notifications for current user / all users  
20. Added switch `--enable-performance-header` to add `X-Response-Time` header in response (\*added in most scenarios)  

## v2.5.10
  
1. Prevented **POST** `/tracksim/update/route` from being loaded when `tracker` plugin is not activated  
2. Fixed `UpdateRoleConnection` not working as expected due to `GetUserInfo` cache  
3. Fixed `DeleteRoleConnection` not working due to invalid `metadata`  
4. Replaced dependency `discord_oauth2` with custom async-enabled class  
5. Added `config.sync_discord_email` to sync email on Discord login  

## v2.5.9
  
1. Added `config.mysql_err_keywords`, removed hardcoded keywords  
2. Removed protected config values from being passed to `external_plugins`  
3. Updated `external_plugins` loading mechanism to take config and return routes & states (app will not be passed for security concerns)  

## v2.5.8
  
1. Fixed BannerGen `app` loading issue  
2. Fixed rare issue of `UpdateRoleConnection`  
3. Renamed `myth_point` to `bonus_point`  
4. Removed **PATCH** `/user/{uid}/discord`, added **PATCH** `/user/{uid}/connections`  
5. Updated `Attention Required` message and added localization  
6. Added `?unsafe` to **PATCH** `/config` for setting protected values to ""  
7. Added `config.security_level` for user session (0 => no additional check | 1 => country check | 2 => ip check)  
8. Improved config validator to prevent duplicate role id  
9. Updated Discord Access Token to store callback url for refresh use  
10. Improved JSON request body error parsing handler  
11. Replaced `/{config.abbr}` with `{config.prefix}` for outgoing API calls announcing Drivers Hub URL  
12. Removed `config.domain`, renamed `config.apidomain` to `config.domain`  

## v2.5.7
  
1. Improved `/user/list` to attach banned info when any connections match  
2. Improved `/user/profile` to attach banned info  
3. Added **GET** `/user/ban/list` and **GET** `/user/ban`  

## v2.5.6
  
1. Fixed incorrect `driver` value in **GET** `/dlog/statistics/chart`  
2. Fixed `email` connection validation  
3. Fixed specific configs are not reloaded after config reload  
4. Added support to multiple embeds for automatic embeds  
5. Merged `member_welcome` into `member_accept`  
6. Added embed validator to prevent 500 errors due to invalid embed config  
7. Added `config.driver_role_add/remove`  
8. Added `config.roles[].order_id`  
**Hint** The order of `roles` no longer relies on `role_id`  

## v2.5.5
  
1. Moved add/remove `member_welcome` discord roles from when driver role is added to when member is accepted  
2. Removed add/remove `member_leave` discord roles from when driver role is removed  

## v2.5.4
  
1. Fixed audit log on user resignation and when removing driver from tracker company  
2. Fixed **PATCH** `/applications/positions` route  
3. Fixed issue updating member's distance point  
4. Fixed dlog summary statistics issue with summing up due to `None` data in one or more columns  
5. Added `?userid` to **GET** `/dlog/export`  
6. Added more triggers of **Role Connection** update: on profile update, driver role addition/removal, member resignation, member dismissal and user deletion  
7. Improved user ban system  
i) When a user connects a banned third-party account, his/her current account will be banned  
ii) Staff may ban users who don't exist in Drivers Hub with their email, discordid etc  
8. Improved user deletion procedure  
i) When a user requests to delete his/her account, it'll be deleted after 14 days  
ii) User may login twice to recover account  
iii) When a staff deletes a user's account, his/her account will be deleted immediately  
9. Updated Discord and Steam callback to return JSON response. Web client should handle callback from third-party servers and forward request params to API for validation  
**Note** For Discord OAuth, web client must add `callback_url` (`redirect_uri`) in request params which is required by Discord  
10. Added automatic config reloader (by detecting file changes) - To solve the issue that config cannot be synced between workers  
11. Allowed public access of **GET** `/config` for partial config that is available to public  
12. Updated config saving/reloading mechanism: New config will be saved to `.saved`, and original config will be replaced by `.saved` on config reload / restart  
13. Added `config.prefix` (default `/{config.abbr}`) for customizable prefix  
14. Updated data type of `config.openapi` to `bool`, hard-coded `openapi.json` path to `{abspath}/openapi.json`  
15. Improved `openapi`  
i) use `servers:[]` instead of `/abbr`  
ii) added `parent-openapi` for multi-hub-doc  

## v2.5.3
  
1. Fixed BannerGen 500 error  
2. Added thousands separator to distance in banners  

## v2.5.2
  
Added Discord Role Connection  
**Hints**  
i) **POST** `/discord/role-connection/enable` must be called to enable this function. (And `/.../disable` may be called to disable it.)  
ii) User may get connected by logging in / connecting Discord.  
iii) Metadata will be automatically updated when a job is submited, distance is added, user logged in or user connected Discord.  
iv) User may manually update metadata with **PATCH** `/member/roles/rank`.  

## v2.5.1
  
1. Added economy-merch  
**Hint** The company owns all the merch. Member will transfer balance to the company when purchasing, and company will transfer balance to member when the member sells the merch.  
2. Added route `/economy` for fetching config  

## v2.5.0
  
1. Improved `/dlog/statistics/summary` query performance  
**Note** Cache expiry for this endpoint was reduced from `120` to `15` (seconds).  
2. Improved `/dlog/statistics/chart` query performance  

## v2.4.4
  
1. Reworked external plugin system  
**Hint** Read `External Plugins` in [README.md](./README.md) and check [example.py](./src/external_plugins/example.py) for reference.  
2. Improved logging  

## v2.4.3
  
1. Fixed redirect route for downloads plugin  
2. Fixed issue banning user who has `NULL` connection(s)  
3. Fixed `scs_convoy`/`multiplayer` detection due to navio->tracksim migration  
4. Prevented transferring to oneself in economy-balance  
5. Added support to ommiting `/{userid}` for `/economy/balance`  
6. Added support to ommiting JSON `owner` for `/.../purchase` (default: `self`)  
7. Improved traceback handler  

## v2.4.2
  
1. Renamed `start_time/end_time` in query param to `after/before`  
2. Added `after/before` query param to **GET** `/divisions`  
3. Improved **GET** `/divisions` response  
4. Renamed `config.server_ip` to `config.server_host`  
5. Added ability to run multiple Drivers Hubs within one server process (multi mode)  
6. Added **POST** `/config/reload` to reload config (**POST** `/restart` is disabled when multi_mode is active)  

## v2.4.1
  
1. Fixed notifications not being sent to `uid = 0`  
2. Fixed errors with MFA (due to `auth_ticket`)  
3. Switched to use `request.app` rather than import it  

## v2.4.0
  
1. Improved how path prefix is defined  
2. Improved how plugin is loaded  
3. Improved routing  
**Note** Renamed **POST** `/user/mfa` to `/user/mfa/enable`, also added plural form to plugin endpoints  
4. Improved TrackSim route saving  
5. Enabled async for `EventNotification` and `ProcessDiscordNotification` (no more threading)  
6. Replaced `tconfig` with `config.__dict__`  

## v2.3.1
  
1. Created a tool to automatically fix ultra-high User ID / UID  
2. Removed support of navio due to truckspace shutdown  
3. Added audit log and notification for blocked deliveries  
4. Added economy transaction history export  
5. Added economy transaction amount limit and trucks/garages price limit  
6. Added TrackSim route saving (with automatic completion for broken routes)  
    This marks the end of Live Tracker, which has been removed from the code. It may be recovered in the future when needed.  
7. Improved error handler to exclude `ProgrammingError` (e.g. invalid SQL syntax) from database errors  

## v2.3.0
  
1. Added `economy` plugin  
2. Bug fixes and improvements  

## v2.2.4
  
1. Fixed `db` creating `ratelimit` TABLE with `ip` COLUMN rather than `identifier` COLUMN  
2. Fixed Discord register is not considering `config.register_methods`  
3. Fixed **GET** `/auth/ticket` adding `user` wrapper  
4. Removed legacy `str: true/false` detection in JSON  
5. Removed `event` announcement type and `event staff` check  
6. Removed `int->str` conversion for `/member/perms`, `/member/ranks`, `/member/roles`, `/division/list`, `/application/types`  
7. Renamed `config.divisions[].point` to `config.division[].points`  
8. Moved `/uptime` to `/status`, added `database` status  
9. Improved `/application/list?all_user=true` to show all applications for `admin` when `config.application_types` is not correctly configured  
10. Added caching to `ratelimit` to reduce database queries when there's excessive traffic (aka `global ratelimit`)  
11. Added string table for audit log and improved existing string table  
12. General improvements on the source code  
13. Dropped `%_old` tables created by `v2.1.0` update  

## v2.2.3
  
1. Fixed banner generator  
2. Fixed application permission control  

## v2.2.2
  
1. Fixed **POST** `/auth/register` not checking `config.register_methods`  
2. Fixed in-Discord-guild check being bypassed when Discord account is not connected  

## v2.2.1
  
Added support to Email/Password registration and updating email  
    Added `smtp_server`, `smtp_port`, `smtp_email`, `smtp_passwd` in config for email credentials  
    Added `email_template.register/update_email/reset_password` as configurable email templates  

    Register with **POST** `/auth/register`  
    After register, confirm email with **POST** `/auth/email` with secret  
    To resend register confirmation email, use **POST** `/user/resend-confirmation`  

    To update email, use **PATCH** `/user/email`  
    To reset password, use **POST** `/auth/reset`  
    Use **POST** `/auth/email` with secret and new password to reset password  

    Secret starting with `rg` refers to `register`, `ue` update email, `rp` reset password, which may be useful for frontend  

## v2.2.0
  
1. Automated `discord_callback_url` and `discord_oauth_url` generation, hence removed it from config  
2. Added function to connect/update Discord account  
    Added `discord_callback` to `config.frontend_urls`  
    Added `?connect_account` request param to `/auth/discord/redirect` to return dynamic oauth url  
    Added route `/auth/discord/connect` which redirects to frontend (`config.discord_callback`) with access code  
    Added route **PATCH** `/user/discord` which takes the access code in JSON and updates Discord account  
**Note** `/auth/discord/connect` needs to be added to `redirect uri` of Discord application besides `/auth/discord/callback` to make it work  
3. Added `config.register_methods[]` to restrict registration methods, accept `email`, `discord`, `steam`  
4. Added `config.steam_api_key` which will be used to get user profile when they register with Steam  
**Hint** Get the API Key at [https://steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)  
5. Added support to Steam registeration  
    When `/auth/steam/callback` is called by a user whose `steamid` is not recognized in database, then register a new account for the user  
    The user's Steam name and avatar will be set as their Drivers Hub default name and profile  

## v2.1.6
  
1. Added support to custom avatar and name (Updated **PATCH** `/user/profile`)  
    Disabled automatic sync to Discord profile on login  
    Disabled default action of syncing to Discord profile, `sync_to_discord=true` in request param is required  
    Added `config.avatar_domain_whitelist[]` to restrict the domain of avatar URL  
**Note** Subdomains are included! For example, if `c.com` is in the list, then `c.com`, `b.c.com`, `a.b.c.com` etc will be accepted.  
    Added `config.allow_custom_profile` to enable/disable the function for regular users, if disabled, then only users with permission `admin`, `hrm`, `hr`, `manage_profile` will be able to update profile for themselves or other users.  
2. Renamed `config.in_guild_check` to `config.must_join_guild`  
3. Added `config.required_connections[]`, accept `email`, `discord`, `steam`, `truckersmp`.  
    Removed `config.truckersmp_bind`  
**Note** Connections are checked when accepting a user as member and creating an application. Steam connection is always required when adding driver role to user due to tracker authentication.  
4. Moved in-Discord-guild check from login to when creating application  

## v2.1.5
  
1. Fixed issue preventing status update of all notifications  
2. Improved ratelimit to identify session with `uid` when available  
3. Updated user object to store and use full avatar URL rather than identifier  
4. Added caching to authorization  
5. Removed bearer token expiration  

## v2.1.4
  
1. Fixed challenge system `required_roles` validation  
2. Updated routes, request json data format, request param format (see table below)  
3. Added `/user/notification/{{notificationid}}` to get specific notification with notification id  
4. Improved code base  

|Route|Remark|
|--|--|
|**GET** `/user`|Moved to **GET** `/user/profile`|
|**GET** `/audit`|Moved to **GET** `/audit/list`|
|**GET** `/user/list`|Renamed `?name` to `?query`|
|**GET** `/member/list`|Renamed `?name` to `?query`|
|**GET** `/user/notification/list`|Renamed `?content` to `?query`|
|**GET** `/audit/list`|Renamed `?operation` to `?query`|
|**GET** `/announcement/list`|Renamed `?title` to `?query`|
|**GET** `/challenge/list`|Renamed `?title` to `?query`|
|**GET** `/downloads/list`|Renamed `?title` to `?query`|
|**GET** `/event/list`|Renamed `?title` to `?query`|
|**DELETE** `/user/password`|Moved to **POST** `/user/password/disable`|
|**DELETE** `/user/mfa`|Moved to **POST** `/user/mfa/disable`|
|**PUT/DELETE** `/user/ban`|Moved `uid` in JSON to path `/user/{uid}/ban`|
|**PATCH** `/user/discord`|Updated and moved `old_discord_id` in JSON to `uid` in path `/user/{uid}/discord`, renamed `new_discord_id` in JSON to `discordid`|
|**DELETE** `/user/connections`|Moved `uid` in request param to path `/user/{uid}/connections`|
|**DELETE** `/user`|Moved `uid` in request param to path `/user/{uid}`|
|**PATCH** `/user/notification/status`|Moved to **PATCH** `/user/notification/{notificationid}/status/{status}`|
|**POST** `/user/notification/{notification_type}/enable`|Moved to **POST** `/user/notification/settings/{notification_type}/enable`|
|**POST** `/user/notification/{notification_type}/disable`|Moved to **POST** `/user/notification/settings/{notification_type}/disable`|
|**PUT** `/member`|Moved to **POST** `/user/{uid}/accept`|
|**PATCH** `/member/roles`|Moved `userid` in JSON to path `/member/{userid}/roles`|
|**PATCH** `/member/point`|Renamed and moved `userid` in JSON to path `/member/{userid}/points`|

## v2.1.3
  
1. Fixed steam/truckersmp connection validation when adding driver role  
2. Fixed error when sending notification to a `uid = None` user  
3. Fixed error when updating user's Discord connection  
4. Updated `/member/roles` to take json data in request  
5. Disabled error webhook on database errors  

## v2.1.2
  
1. Fixed `AutoMessage` cannot be sent when using webhook  
2. Removed `member_leave` on driver role removal, removed `member_accept` and `member_welcome` on driver role addition, moved `member_accept` and `member_welcome` to be sent on member acceptance  
3. Renamed `config.team_update` to `config.member_accept`, which is sent once the member is accepted  
**Hint:** `member_accept` and `member_welcome` are both sent when member is accepted, `member_leave` is sent when member resigns or is dismissed  

## v2.1.1
  
1. Fixed upgrader failure due to `./upgrades/` does not exist by removing file log  
2. Fixed application webhook being sent to division webhook  
3. Fixed application permission issue  
4. Fixed `user.activity` being `null`  
5. Fixed multilang unable to handle `None` requests  
6. Fixed `v2_1_0` upgrader not creating DATA DIRECTORY for `application` and removing `nxtuserid` in settings  
7. Created `v2_1_1` upgrader to set DATA DIRECTORY for `application` and add `nxtuserid` back to settings  

## v2.1.0
  
**Breaking changes** ⚠️  
**Note: This is a release focusing on updating the user system, to allow every user to have a uid and use uid to identify users, rather than using discordid.**  
**Warning⚠️:** Major database structure updates involved, **backup** the database before upgrading to this version.  
**Hint:** It's no longer necessary to place an `upgrade.py` in the directory to upgrade, the upgrader is coded into the main program, which will be executed automatically.  

- Database Changes

1. Reordered columns in `user` table, added `uid` before `userid`. `uid` will be assigned to everyone with an `AUTO INCREMENT` property, `userid` will only be given to accepted members  
2. Swapped order of `update_staff_timestamp` and `update_staff_userid` in `application` table  
3. Changed tables using `discordid` to identify users to use `uid`.  
**Affected Tables:** `user_password`, `user_activity`, `user_notification`, `banned` (it's complex), `application`, `session`, `auth_ticket`, `application_token`, `settings`  
4. Changed `auditlog` using `userid` to identify users to use `uid`  
5. Renamed `temp_identity_proof` to `auth_ticket`.  
6. Changed `steamid,truckersmpid=-1/0` to `NULL`  
7. Added `AUTO_INCREMENT` property to `user.userid`, `user_notification.notificationid`, `dlog.logid`, `announcement.announcementid`, `application.applicationid`, `challenge.challengeid`, `downloads.downloadsid`, `event.eventid`, thus removed `nxtuserid`, `nxtnotificationid`, `nxtlogid`, `nxtappid`, `nxtannid`, `nxtchallengeid`, `nxtdownloadsid`, `nxteventid` in settings  

- API Changes

1. Added `?uid` query param to **GET** `/member/banner`, **GET** `/user`, **PATCH** `/user/profile`  
2. Added `uid` to `order_by` of **GET** `/user/list`, **GET** `/member/list`  
3. Changed `?discordid` query param to `?uid` for **DELETE** `/user/mfa`, **DELETE** `/user`  
4. Changed `discordid` in json data of **PUT** `/member`, **PUT**/**DELETE** `/user/ban`, **DELETE** `/user/connections` to `uid`  
5. Moved `?userid` query param of `/member/dismiss` to path (`/member/dismiss/{userid}`)  
6. Moved `uid` in json data to query param for **DELETE** `/user/connections`  
7. Renamed `/user/tip` to `/auth/ticket`

## v2.0.1 (pre-release)
  
1. Fixed user activity caching issue  
2. Added user language cache  

## v2.0.0 (pre-release)
  
**Breaking changes** ⚠️  
**Note: This is a pre-release focusing on request and response formats, major functionalities are not modified, there will be updates on the user system in v2.1.0.**  

1. Changed request data from `form` to `json` to better format complex data  
**Note** Form data will be rejected. You must add header `Content-Type: application/json`.  
**Hint** The data format for endpoints won't be affected, but some containing complex data will be modified, as shown in the table below.  
|Route|Affected Fields (Hint: `object` is `json`)|
--|--|
|**PATCH** `/config`|`config` (`string`     `object`)|
|**POST** `/application`|`data`->`application` (`string`     `object`)|
|**POST** `/challenge`|`job_requirements` (`string`     `object`), `required_roles` (`string`     `object` (`list`))|
|**PATCH** `/challenge/{challengeid}`|`job_requirements` (`string`     `object`), `required_roles` (`string`     `object` (`list`))|
|**PATCH** `/event/{eventid}/attendees`|`attendees` (`string`     `object` (`list`))|

2. Changed response format  
i) Removed `error: bool` field. Error status will only be reflected in **status code** (non-2xx responses).  
ii) Removed `descriptor: string` field. Added `error: string` field to explain the error, same as the original `descriptor: string` field.  
iii) Moved data inside `response: object` out.  
iv) On success, the response will be `204 No Content` if no message or data is returned.  
v) Removed `string     integer` conversion for most integers, known large integers like `discordid` will still be converted to string.  
vi) Changed `"-1"` or `""` or `"N/A"` values to `None`  
**Note** If you are using `-1` as `None` in your requests, you must remove it or you'll get incorrect responses!  
**Examples:**  
i) Unauthorized Error  
**STATUS: 401** `{"error": "Unauthorized"}`  
~~**Old format** `{"error": true, "descriptor": "Unauthorized"}`~~  
ii) Get Info  
**STATUS: 200** `{"info": "Some info here"}`  
~~**Old format** `{"error": false, "response": {"info": "Some info here"}}`~~  
iii) Update Info (Without a message returned)  
**STATUS: 204**  
~~**Old format** `{"error": false}`~~  
iv) Update Info (With a message returned)  
**STATUS: 200** `{"message": "Updated"}`  
~~**Old format** `{"error": false, "response": {"message": "Updated"}}`~~  

3. Changed request params name / format  
|Route|Affected Params|  
--|--|
|**GET** `/dlog/statistics/chart`|`?end_time`     `?before`|  
|**GET**/**DELETE** `/dlog`|`?logid` moved to path (`/dlog/{logid}`)|
|**GET**/**PATCH**/**DELETE** `/announcement`|`?announcementid` moved to path (`/announcement/{announcementid}`)|
|**GET**/**PATCH**/**DELETE** `/application`|`(form)applicationid` moved to path (`/application/{applicationid}`)|
|**PATCH** `/application/status`|`(form)applicationid` moved to path (`/application/{applicationid}/status`)|
|**GET**/**PATCH**/**DELETE** `/challenge`|`?challengeid` moved to path (`/challenge/{challengeid}`)|
|**PUT**/**DELETE** `/challenge/delivery`|`?challengeid,(form)logid` moved to path (`/challenge/{challengeid}/delivery/{logid}`)|
|**GET**/**PATCH**/**DELETE** `/downloads`|`?downloadsid` moved to path (`/downloads/{downloadsid}`)|
|**GET**/**PATCH**/**DELETE** `/event`|`?eventid` moved to path (`/event/{eventid}`)|
|**PUT/DELETE** `/event/vote`|`?eventid` moved to path (`/event/{eventid}/vote`)|
|**PATCH** `/event/attendees`|`?eventid` moved to path (`/event/{eventid}/attendees`)|

4. Updated routes  
|Route|Remark|
--|--|
|**GET** `/member/list/all`|Removed|
|**GET** `/event/all`|Removed|
|**GET** `/division?logid`|Splitted to **GET** `/division` and **GET** `/dlog/{logid}/division`|
|**POST** `/division?divisionid` (`logid` in form)|Renamed to **POST** `/dlog/{logid}/division/{divisionid}`|
|**GET** `/downloads/{secret}`|Renamed to **GET** `/downloads/redirect/{secret}`|
|**PATCH** `/event/{eventid}/vote`|Splitted to **PUT**/**DELETE** `/event/{eventid}/vote`|
|**PATCH** `/event/{eventid}/attendee`|Renamed to **GET** `/event/{eventid}/attendees`|

5. Updated response/object format  
**Hint** These formats apply whenever the object is returned, which greatly improves the API's usability and could reduce the amount of requests.  
i) Activity `{status: str, last_seen: int}` or `None`  
ii) Ban `{reason: str, expire: int}` or `None`  
iii) User `{userid: int, name: str, email: str, discordid: str, steamid: str, truckersmpid: int, avatar: str, bio: str, roles: list, activity: dict, mfa: bool, join_timestamp: int}`  

6. Removed object wrapper including `user: {}`, `application: {}`, `dlog: {}`, `downloads: {}`, `event: {}`  
7. Replaced completed member list (`completed`) in `/challenge/list` with the number of completed members, the detailed list could be fetched with `/challenge/{challengeid}`  
8. Replaced voted member list (`votes`) and attendees (`attendees`) in `/event/list` with the number of voted members and attendees, the detailed list could be fetched with `/event/{eventid}`  
9. Renamed `detail` in **GET** `/application/{applicationid}` response to `application`, renamed `data` in **POST** `/application` request to `application`  
10. Fixed `/member/roles/rank` not converting distance to imperial when `config.distance_unit = "imperial"`  
11. Fixed permission control of updating application status  
12. Added function to delete applications  
13. Allowed admin to bypass division driver check (admins won't be counted in statistics unless they have the division role)  
14. Other improvements on response and bug fixes, check [openapi.json](./openapi.json) for more info.  

## v1.22.15
  
1. Increased database connection timeout by 1 second (to 2 seconds)  
2. Fixed traceback log corrupts when code is compiled  

## v1.22.14
  
1. Improved error formatter to prevent corrupted results  
2. Fixed error when adding/removing a role that is not recognized  

## v1.22.13
  
1. Fixed `point2rank` seires functions going wrong when there's only one rank  
2. Fixed error not being printed when `config.webhook_error == ""`  

## v1.22.12
  
1. Removed 50 session limit  
2. Improved application token to allow multiple applications  
3. Fixed the bug that Discord notification is not shown as disabled when the system disables it due to unable to DM  
4. Fixed `mfa_invalid_otp` issue when the OTP starts with `0`  

## v1.22.11
  
1. *\[BannerGen\]* Changed `Since YYYY/(M)M/(D)D` to `Joined: YYYY/MM/DD`  
2. *\[BannerGen\]* Replaced license fonts with open fonts to prevent copyright issues  
|Old Font|Supported Glyphs|New Font|Supported Glyphs|  
--|--|--|--|
|`Consola` + `Sans Serif`|3765|`Ubuntu Mono`|1256|  
|`Impact`|720|`Anton`|978|  
|`UniSans`|458|`Open Sans`|1010|  

## v1.22.10
  
1. Prevented restarting database connection pool for multiple times when it is already restarting  
2. Removed original 500 error handler as middleware is handling errors  
3. Fixed `discord_notification_enabled` notification not being sent  
4. Added 428 error if bot is unable to DM user when enabling Discord notification  
5. Added `config.webhook_error` to send non-database errors to Discord  
6. Added error formatter before printing the error to log  

## v1.22.9
  
1. Removed `wait_timeout` that closes connections  
**Note** Closed connections are not released to pool  
2. Added pool restart before restarting service when pool is corrupted  

## v1.22.8
  
1. Added legacy database connection pool management solution back  
2. Added timeout when acquiring connection from pool  
3. Added try/except when getting current config to return backup config in case local file is broken  

## v1.22.7
  
1. Merged 500 error handler into middleware  
2. Added database connection close on request fail  

## v1.22.6
  
1. Fixed `Unknown Error` on Discord callback when `email` is not provided in form data  
2. Added `config.whitelist_ips` to authorization country check and ratelimit  
3. Added middleware to requests to better manage database connection pool  
4. Removed legacy database connection pool management solution  
5. Enabled TrackSim telemetry tracking  
6. Disabled `guest` token authorization  
7. Removed unnecessary imports and strings  

## v1.22.5
  
1. Fixed TrackSim setup webhook  
2. Added `allowed_tracker_ips` update on TrackSim setup  

## v1.22.4
  
1. Removed try / except when adding job to database  
2. Improved delivery rule block handling  

## v1.22.3
  
1. Removed `exit` on restart and left the `restart` job to `systemctl`  
2. Fixed error when a navio / tracksim webhook post is rejected  
3. Fixed config allowing `tracker_api_token` and `tracker_webhook_secret` being empty  

## v1.22.2
  
1. Fixed `has_police_enabled` error when exporting dlog  
2. Fixed database connection timeout due to slow `requests` response  

## v1.22.1
  
1. Renamed `config.navio_*` to `config.tracker_*`  
2. Added async requests  
3. Added full role management for users with highest role  
4. Added `view count` to delivery log  
5. Added TrackSim setup, webhook, add/remove driver  
6. Added dual-tracker support (TrackSim / Navio)  

## v1.21.22
  
1. Improved restart handler  
2. Added `config.mysql_pool_size`  
3. Renamed `config.allowed_navio_ips` to `config.allowed_tracker_ips`  
4. Added `delivery_rules` to config whitelist  

## v1.21.21
  
1. Improved error handler  
2. Prevented index to connect to database when `Authorization` header is not provided  
3. Renamed `reload` to `restart`  
4. Preparations for switching tracker  

## v1.21.20
  
1. Converted database error to `503` error  
2. Fixed `500` error handler exception  
3. Added `422` error handler  
4. Added `minimum/maximum_average_distance/fuel` to challenge plugin  

## v1.21.19
  
1. Added `500 Internal Server Error` handler  
2. Added auto-restart on too many errors  
3. Added `wait_timeout` and `lock_wait_timeout` for db connections  
4. Improved **GET** `/dlog/statistics/chart`  

## v1.21.18
  
1. Fixed file encoding error  
2. Fixed duplicate ID issue  

## v1.21.17
  
Optimized database connection management  

## v1.21.16
  
Implemented database connection pool for better stability  

## v1.21.15
  
1. Added asyncio support to database operation  
2. Added `shutdown` event handler  
3. Removed dependency `fonttools` and improved code to check if glyph is in a static font file  
4. Removed dependency `iso3166` and included dict `ISO3166_COUNTRIES`  

## v1.21.14
  
1. Fixed database connection issue caused by v1.21.13  
2. Fixed bug `navio_api_error` not declared  
3. Changed **PATCH** `/user/name` to **PATCH** `/user/profile`, added avatar update on **PATCH** `/user/profile`  
4. Improved code base  

## v1.21.13
  
Improved database connection management and reduced resource consumption  

## v1.21.12
  
1. Prevented crash on certain types of invalid config  
2. Fixed **GET** `/downloads/redirect` 500 error when downloadable item not found  
3. Other bug fixes and minor improvements  

## v1.21.11
  
Added `end_time` request param to **GET** `/dlog/statistics/chart`  

## v1.21.10
  
1. Fixed manually-added distance leading to inaccurate result of leaderboard division point  
2. Fixed challenge completed status not adding to personal one-time / recurring challenge  

## v1.21.9
  
Removed unncessary `convert_quotation` that led to `\'` visible by user  

## v1.21.8
  
1. Improved internal / external API handling to prevent 500 errors when request failed  
2. Added `config.member_leave` to automate Discord message & role updates when driver leaves  
3. Added automatic rank role removal when driver leaves  
*Note: "leave" is defined by either driver role is removed, member resigns, or member is dismissed.  

## v1.21.7
  
1. Fixed **POST** `/user/tip` 500 error  
2. Fixed **GET** `/division` returns incorrect data  
3. Endpoint Route & Methods: Updated for better readability  
|Old|New|  
--|--|
|**PUT** `/auth/tip`|**POST** `/user/tip`|  
|**PUT** `/user/notification/status`|**PATCH** `/user/notification/status`|  
|**PATCH** `/user/notification/{{notification_type}}/enable`|**POST** `/user/notification/{{notification_type}}/enable`|  
|**PATCH** `/user/notification/{{notification_type}}/disable`|**POST** `/user/notification/{{notification_type}}/disable`|  
|**PUT** `/event/vote`|**PATCH** `/event/vote`|  

## v1.21.6
  
1. Fixed the bug being unable to parse `204` response which led to errors  
2. Added numeric value check to prevent large value being rejected by database  
3. Updated database datatype (mainly `discordid` to `BIGINT UNSIGNED`)  
4. Changed `distance` in `config.ranks` to `points`  

## v1.21.5

1. *\[BannerGen\]* Prevented sending request to BannerGen when cache exists  
2. *\[BannerGen\]* Improved avatar caching mechanism  
3. User activity: Changed `user_{userid}` to `member_{userid}`  
4. Rate limit: Added `X-RateLimit-Reset` and `X-RateLimit-Reset-After` header for non-429 responses  
5. User: Added **PATCH** `/user/name` to update username to latest Discord user name / server nickname  
6. Event: Added `first_event_after` request param for better ordering  
7. Discord Integration: Added error notification when fails to update roles  
8. Discord Integration: Added `config.use_server_nickname`, if `true`, then use nickname in Discord server  
9. Configuration: Added config validator to use default value for missing fields  
10. Endpoint Route & Methods: Updated for better readability  
|Old|New|  
--|--|
|**PUT** `/reload`|**POST** `/reload`|
|**PUT** `/auth/tip`|**POST** `/user/tip`|
|**GET** `/auth/tip`|**GET** `/user/tip`|
|**PUT** `/auth/mfa`|**POST** `/user/mfa`|
|**DELETE** `/auth/mfa`|**DELETE** `/user/mfa`|
|**DELETE** `/member/resign`|**POST** `/member/resign`|
|**DELETE** `/member/dismiss`|**POST** `/member/dismiss`|

## v1.21.4
  
1. Improved Discord Notification to send batched embeds (less messages, more embeds)  
2. Added distance-based challenge  
3. Fixed various bugs of challenge plugin  

## v1.21.3
  
1. *\[BannerGen\]* Merged `ConsolaBold` with `SansSerif` to support a larger character set  
2. *\[BannerGen\]* Added unicode normalization to remove decoration to make more characters drawable  
3. *\[BannerGen\]* Added division text length limiter to prevent overflowing into logo image  
4. *\[BannerGen\]* Increased precision of changing `username` and `highest role` font size to 1 (originally 5)  
5. *\[BannerGen\]* Improved `highest role` positioning algorithm  
6. *\[BannerGen\]* Optimization (avg. 98ms/banner, originally 460ms/banner)  
7. Fixed **PATCH** `/config` cannot update `config.language`  
8. *[User]* Fixed **GET** `/user` activity adding a trailing ")"  
9. Added config keys sorter to better organize config file  
10. *[Member]* Added `already_have_discord_role` response for **PATCH** `/member/roles/rank` when member is under distance required by lowest rank  
11. *[Dlog]* Added `order_by` (`logid`, `max_speed`, `profit`, `fuel`, `distance`) request param to **GET** `/dlog/list`  
12. Added support to Discord API v10  

## v1.21.2
  
Improved **GET** `/dlog/statistics/chart`, removed `scale` param, added `ranges` and `interval` params for better customizability  

## v1.21.1
  
1. Fixed the bug that **PATCH** `/member/roles/rank` is always returning `discord_integrations_disabled` response  
2. Changed `unauthorized` responses due to insufficient permission to `forbidden`  
3. Updated upgrader to require `upgrade` parameter in `sys.argv`  
4. Added `config.language` to set company language for delivery log embed (audit log will always be in English)  
5. Updated activity info to program-friendly (frontend need to be updated to parse it)  
6. *[Challenge]* Added notification when challenge reward points is updated  
7. *[Dlog]* Added endpoint to delete deivery log: **DELETE** `/dlog`  
8. *[User]* Added endpoint to set and get language: **GET**, **PATCH** `/user/language`  
9. Updated `ml.translate` to consider user language if set (if not, then fall back to `Accept-Language`)  
10. Added full multilang support for all notification  
11. Polished Discord Notification of Login & Application & Division (better using embed)  
12. Added per-function notification settings  
13. Added `multilang_helper` to better manage translations internally  

## v1.20.3
  
1. Fixed **GET** `/config` 500 error when content related to disabled plugins are not in config  
2. Fixed event notification sending more than one  
3. Made it possible to send event notification for delayed event  
4. Added translation for `Unknown Error`  
5. Enabled thread daemon to make shutdowns faster  

## v1.20.2
  
Fixed the bug that program cannot shut down fully  

## v1.20.1

1. *[Auth]* Fixed the bug that ban check is not performed on steam & password login  
2. *[Auth]* Fixed the bug that referrer check does not work  
3. *[Auth]* Increased session life to 30 days  
4. *[Auth]* Increased max session count to 50  
5. *[Auth]* Removed endpoint **GET** `/token/all`, added endpoint **GET** `/token/list`  
6. *[Auth]* Added `country`, `user_agent` and `last_used_timestamp` to session table  
7. *[Auth]* Changed session IP check to country check  
8. *[Auth]* Added `last_used_before` request param to **DELETE** `/token/all`  
9. Added Discord Bot Token Validation to prevent invalid tokens from being used  
10. Added `config.allowed_navio_ips`  
11. Added translation for all endpoints (except Navio Webhook)  
12. Added Russian, Turkish and Italian translation  
13. Improved rate limit response  
14. Added user-controllable Discord Notification and removed `discord_bot_dm` from config  
i) Added endpoint **PATCH** `/user/notification/{str:notification_type}/enable`, **PATCH** `/user/notification/{str:notification_type}/disable`,   **GET** `/user/notification/settings`  
ii) Discord Notifications use the same content as Drivers Hub Notifications  
iii) Notifications are queued up to prevent Drivers Hub being rate limited by Discord API.  
iv) If Drivers Hub fails to send a DM, Discord Notification (including Event Notification) will be disabled.  
v) All previously enabled-by-default Discord DMs have been disabled. User will have to manually enable Discord Notification to make DMs work  

## v1.19.6
  
Hard-coded English String Table  

## v1.19.5
  
1. Fixed the bug that **GET** `/dlog/list` returns same delivery for multiple times due to challenge record  
2. Added `public_details` to **GET** `/challenge` and **GET** `/challenge/list`  

## v1.19.4
  
1. *\[BannerGen\]* Reduced workers to 1 worker  
2. *\[BannerGen\]* Reduced resolution to 1700x300  
3. *\[BannerGen\]* General improvements on output  
4. *[Auth]* Fixed the bug that users whose names contain `'` fail to register  
5. *[Application]* Added `status` request param to **GET** `/application/list`  
6. Added item wrapper to **GET** `/announcement`, **GET** `/application`, **GET** `/challenge`, **GET** `/downloads`, **GET** `/event`, **GET** `/user`, **GET** `/dlog`  
7. Changed integer response to string response for **GET** `/member/perms`  
8. Loosened API rate limit  

## v1.19.3
  
*[Challenge]* Added new challenge type `Personal (Recurring)` (original `Personal` type renamed to `Personal (One-time)`), which supports single challenge being completed for multiple times and receiving multiple rewards  

## v1.19.2
  
1. Fixed the bug that `is_private` is not updated when **PATCH** `/announcement`  
2. Fixed **GET** `/dlog/list` and **GET** `/dlog/export` shows pending division info  
3. Added 150,000-character limit for config  

## v1.19.1
  
1. *[Dlog]* Improved `dlog` to support empty delivery log data (detail)  
2. *[Auth]* Updated **GET** `/auth/discord/callback` and **GET** `/auth/steam/callback` **Referer Check** to only make sure the request is not direct  
3. *[Auth]* Added **Referer Check** to **GET** `/auth/steam/connect`  
4. *[Auth]* Added **In-guild Check** to **POST** `/auth/password` and **GET** `/auth/steam/callback`  
5. *[Auth]* Improved **In-guild Check** to return `must_join_discord` error when Discord API Response Code is `404`  
6. Added `X-Audit-Log-Reason` header when updating User Discord Roles through Discord API  
7. *[Member]* Added `Navio API Error` to response of **PATCH** `/member/roles` (e.g. Steam profile is not public)  
8. *[Member]* Added `last_seen` to `order` parameter of **GET** `/member/list` and `last_seen_after` parameter to **GET** `/member/list`  
9. *[Dlog]* Improved Delivery Log Export (Added many more details, including division & challenge)  
10. *[Downloads]* Reworked **downloads** plugin, added item-based management and downloads click count  
11. Added per-function (endpoint) permission control (Note that existing integrated permissions are not modified)  
|Endpoint|Added Permission|
--|--|
|**GET**, **PATCH** /config|config|
|**PUT** /reload|reload|
|**DELETE** /auth/mfa|disable_user_mfa|
|**PUT** /member|add_member|
|**PATCH** /member/roles|update_member_roles|
|**PATCH** /member/point|update_member_points|
|**DELETE** /dismiss|dismiss_member|
|**GET** /user/list|get_pending_user_list|
|**PUT**, **DELETE** /user/ban|ban_user|
|**PATCH** /user/discord|update_user_discord|
|**DELETE** /user/connections|delete_account_connections|
|**DELETE** /user|delete_user|
|**PATCH** /application/positions|update_application_positions|

12. Optimized database query  
|Endpoint|Note|
--|--|
|**GET** /dlog/list|Improved division & challenge query, added division & challenge name in response|
|**GET** /user/list|Improved banned info query|

## v1.18.3
  
1. Fixed **GET** `/challenge/list` param `must_have_completed` not working correctly  
2. Changed order of `challenge[].completed` to `points DESC, timestamp ASC, userid ASC`  

## v1.18.2
  
1. *[Event]* Separated single-event query from event-list query  
2. *[Announcement]* Separated single-announcement query from announcement-list query  
3. *[User]* Changed **PUT** `/user/unban` to **DELETE** `/user/ban`  
4. *[User]* Changed `ban.ban_reason` response to `ban.reason`  
5. *[Challenge]* Added `completed` field in **GET** `/challenge` response  
6. *[Challenge]* Fixed various bugs of this plugin  
7. Added form string length limit  

## v1.18.1

1. *[Challenge]* Added multiple item support to `source_city_id`, `source_company_id`, `destination_city_id`, `destination_company_it`, `cargo_id`  
2. Added user activity  
3. Added notification system  

## v1.17.1

1. *[Member]* Fixed **PATCH** `/member/roles/rank` giving highest role when there is no `point = 0` role
2. *[Member]* Added automatic redirect for `/member/banner` to `?userid=` when query param is not `userid`  
3. *[Announcement]* Added `order_by` (`announcementid` or `title`) and `title` (for searching) parameter to **GET** `/announcement`  
4. *[Division]* Moved `divisionid` to request param instead of form data for **POST** `/division`, **PATCH** `/division`  
5. *[Division]* Added `page`, `page_size`, `divisionid` parameter to **GET** `/division/list/pending`  
6. *[Division]* Added division info to **GET** `/dlog`  
7. *[Division]* Added detailed division info to **GET** `/dlog/list`, removed `division_validated` field  
8. *[Division]* Added `division` request param to `/dlog/list` to query division delivery, removed `recent_deliveries` from **GET** `/division`  
9. *[Event]* Added `title` (for searching) parameter to **GET** `/event`  
10. Improved audit log  
11. *[User]* Updated **DELETE** `/user`, moved `discordid` to request params. If specified, then delete user with the Discord ID. Otherwise delete user themselves. This will not delete a member  
12. *[Config]* Added `config.delivery_rules` with `max_profit`, `max_speed`, `action` sub-keys. `action` could be `block`, `drop`, `bypass`. `block` will reject the delivery from webhook post, `drop` will drop the item that violated the rule, `bypass` will accept the delivery (or, disable the rules). `drop` will only work for `max_profit`, by reducing it to `0`.  
13. *[Challenge]* Added new plugin: **challenge**  

- Database

1. *[Announcement]* Plain text for `title` and compressed `content`  
2. *[Division]* Compressed `message`  
3. *[Downloads]* Compressed `downloads`  
4. *[Event]* Plain text for `title`, `departure`, `destination` and compressed `link`, `description`  

## v1.16.1
  
1. Fixed application setting `user[userid=0]` as `last_update_staff` when nobody updated the application  
2. Fixed config update corruption due to multiple workers  
3. Fixed **PATCH** `/user/discord` that removes account when `old_discord_id = new_discord_id`  
4. Fixed **PUT** `/user/ban` always using "Unknown User" in audit log  
5. Removed `bot_application_received` message  
6. Removed **PUT** `/config/reset` endpoint  
7. Added MFA support to **PATCH**, **DELETE** `/token/application`, **DELETE** `/user/password`  
8. Tightened rate-limit of **GET** `/member/banner` to 2r/10s (from 30r/180s), also lowered `bannergen` workers to 3  
9. Improved rate-limiter, added 10-minute ban for IPs surpassing 150r/m  

## v1.15.11
  
1. Removed detailed per-user statistics from **GET** `/division`  
2. Updated **GET** `/dlog/leaderboard` response to include `total` and `rank` in `points`  
3. Improved **PATCH** `/division` to prevent overwriting `divisionid` to invalid id  
4. Added 100-row limit to **GET** `/division/list/pending` to prevent large response  

## v1.15.10
  
1. Fixed speed limit not working for `/dlog/list` and `/dlog/leaderboard`  
2. Added `status` parameter `(0: All | 1: Delivered | 2: Cancelled)` to `/dlog/list`  
3. Added `status` field to `/dlog/list` response  

## v1.15.9
  
1. Fixed announcement plugin 500 error  
2. Added avatar to announcement and audit log embed  

## v1.15.8
  
Moved Steam & TruckersMP connection check to when adding driver role instead of when accepting user as member  

## v1.15.7
  
Improved response format  
**GET** `/audit` - Added detailed user info  
**GET** `/auth/tip` - Added detailed user info  
**GET** `/dlog` - Added detailed user info  
**GET** `/dlog/list` - Added detailed user info, changed `isdivision` to `division_validated`  
**GET** `/dlog/leaderboard` - Improved response format  
**GET** `/user/list` - Improved response format  
**GET** `/member/list` - Added `roles`, removed `highestrole` which should be calculated by frontend  
**GET** `/announcement` - Added detailed author info  
**GET** `/application` - Added detailed creator / staff info  
**GET** `/application/list` - Added detailed creator / staff info  
**GET** `/division` - Added detailed user / staff info, removed `user_is_staff` which should be calculated by frontend  
**GET** `/division/list/pending` - Added detailed user info  

## v1.15.6
  
1. Improved TOTP function to accept OTP of bigger time range  
2. Added MFA secret base32 check  
3. Added MFA support (if enabled) to **PATCH** `/user/password`  

## v1.15.5
  
Fixed leaderboard skipping rank due to deleted users  

## v1.15.4
  
Fixed **GET** `/config` returning malformed `roles` data  

## v1.15.3
  
Fixed bannergen showing username as company name  

## v1.15.2
  
1. Fixed **POST** `/reload` 500 error when MFA is not enabled  
2. Changed `tip` form field to `token` for **POST** `/auth/mfa`  

## v1.15.1
  
Added **Multiple Factor Authentication**  
i) New endpoints: **PUT**, **POST**, **DELETE** `/auth/mfa`  
ii) Endpoint to check if user has MFA enabled: **GET** `/user`  
iii) Endpoints that support MFA if enabled: **POST** `/auth/password`, **GET** `/auth/discord/callback`, **GET** `/auth/steam/callback`, **DELETE** `/member/resign`  
iv) Endpoint that requires MFA: **POST** `/reload`  

## v1.14.5
  
1. Removed 'vtc' element  
2. Added `points` field to **GET** `/event` response  
3. Added `config.discord_bot_dm` (boolean) to enable / disable bot DM  
4. Config format update  
a) Item name changes  
|Old Name|New Name|  
---|---|  
|vtc_abbr|abbr|
|vtc_name|name|
|vtc_logo_link|logo_url|  

b) Updated `roles` format to `[{"id": "id", "name": "role"}]`  

## v1.14.4
  
1. Fixed `isdivision` (boolean) response being stringified to "True" / "False"  
2. Added `Unknown Error` response to **GET** `/auth/discord/callback` to prevent `Internal Server Error`  
3. Added `name` parameter to **GET** `/user/list` request for querying username  
4. Added User ID to application messages  
5. Added `backup` field to **GET** `/config` response for getting old config (currently loaded) before reload  
6. Added endpoint **PUT** `/config/reset` to revert config to old config (currently loaded)  
7. Added `frontend_urls` to config to customize frontend URL on redirect / clickable link  
8. Updated partial string table items  
9. Updated `images` for events to `description`  
10. Renamed database columns for better readability  
|Table|Old Column Name|New Column Name|
--|--|--|
|user|joints|join_timestamp|
|banned|expire|expire_timestamp|
|announcement|aid|announcementid|
|announcement|atype|announcement_type|
|announcement|pvt|is_private|
|application|apptype|application_type|
|application|submitTimestamp|submit_timestamp|
|application|closedBy|update_staff_userid|
|application|closedTimestamp|update_staff_timestamp|
|division|requestts|request_timestamp|
|division|updatets|update_timestamp|
|division|staffid|update_staff_userid|
|division|reason|message|
|event|tmplink|truckersmp_link|
|event|mts|meetup_timestamp|
|event|dts|departure_timestamp|
|event|img|description|
|event|pvt|is_private|
|event|eventpnt|points|
|ratelimit|firstop|first_request_timestamp|
|ratelimit|opcount|request_count|

## v1.14.3
  
Improved role & config update validator to prevent admin users removing their own admin permission  

## v1.14.2
  
Added steam login  

## v1.14.1
  
1. Improved config validation on **PATCH** `/config`  
2. Removed automatic reload on **PATCH** `/config`  
3. Added **Temporary Identity Proof** (`/auth/tip`)  

## v1.13.2
  
1. Added 400 response when required form data is not provided  
2. Added "real deletion" for `announcement` and `event` instead of changing the id to negative numbers  
3. Improved API Documentation  

## v1.13.1
  
1. Added ability to edit meta elements of automated embeds in Discord (Welcome, Team Update, Rank Update)  
2. Added ability to switch between webhook and bot for automated embeds in Discord (Welcome, Team Update, Rank Update)  
3. Updated partial endpoint path or method  

## v1.12.9
  
1. Fixed the bug that updating event point without updating attendee doesn't work  
2. Added **DELETE** `/user/password` endpoint and removed the ability to disable password login by passing empty password to **PATCH** `/user/password`  

## v1.12.8
  
1. Fixed 500 error when submitting division validation request  
2. Fixed 500 error when Drivers Hub gets error from Discord getting user data (`/auth/discord/callback`)  
3. Fixed some 500 errors when trying to convert non-int to int  

## v1.12.7
  
Improved endpoint path and response format for better readability

## v1.12.6
  
Improved Banner Generator:  
i) Fixed 500 error when image is invalid  
ii) Fixed transparent logo background becoming solid in some cases  
iii) Improved rounded avatar generation and added transparency  

## v1.12.5
  
1. Fixed 500 error on `/user` when `config.privacy = false` and no authorization header is provided  
2. Fixed `/member/steam` showing non-member information  

## v1.12.4
  
1. Fixed 500 error on `/dlog/stats` when `config.privacy = true`  
2. Added Discord Login requirement to `/user/discord`, `/user/connection`, `/user/delete`, `/member/dismiss`, `/member/resign`  
3. Reduced cache expire time from 300 seconds to 120 seconds for `/dlog/stats` and `/dlog/leaderboard`  

## v1.12.3
  
Improved leaderboard ordering  

## v1.12.2
  
1. Added cache for `/dlog/stats` (5min), `/dlog/leaderboard` (5min), `/user/banner` (1hr)  
2. Removed statistics in `/user`  
3. Removed `driver` table  
4. Improved database index creation  
5. Fixed some bugs  

## v1.12.1
  
1. Added Myth Point  
2. Changed getting `distance` and `eventpnt` from `driver` table to calculating them with record  
3. Recoded `/dlog/leaderboard`  
4. Fixed some bugs  

## v1.11.5
  
1. Fixed the bug that leaderboard is not loading  
2. Improved authentication system  
3. Removed possibility to add event point and division point using `/member/point`  
4. Added possibility of showing `distance` added with `Update Member Point` on time-ranged leaderboard  
5. Added `hr` permission to `/member/point`  

## v1.11.4
  
Improved Banner Generator to save memory  

## v1.11.3
  
1. Merged `/member` and `/user` to `/user` for both member and public user, added `discordid`, `steamid`, `truckersmpid` parameter  
2. Added `config.privacy` to select whether to show / hide member information in public, including: `/member/steam`, `/members`, `/user`, `/dlog`, `/dlogs`  
3. Added `userid` parameter to `/dlog/stats` to query detailed user statistics (require `config.privacy = false`)  
4. Added `/user/banner` for auto-generated profile banner (require `banner` in `config.enabled_plugins`)  
5. Updated ratelimit  
6. Updated API error response  

## v1.11.2
  
Added requirement to login with discord to revoke specific / all token  

## v1.11.1
  
1. Improved `application` plugin:  
i) Added support to per-type webhook  
ii) Added support to per-type staff role  
iii) Removed reservation for type ID 1~4 (driver, staff, loa, division)  
iv) Added `note` (`driver`) for `config.application_types` as a substitute of reservation  
2. Improved authentication  
i) Added **DELETE** `/token/all` endpoint to revoke all sessions  
ii) Added **DELETE** `/token/hash` endpoint to revoke specific token with sha256 hash  
iii) Added **GET** `/token/all` endpoint to get all token sha256 hash, ip and timestamp  
iv) Added session limit to ensure user have a maximum of 10 active sessions  

## v1.10.10
  
Added `revoke-all-token` when updating password  

## v1.10.9
  
Removed regex email validation  

## v1.10.8
  
Fixed the bug that application webhook contains words in applicant's language  

## v1.10.7
  
1. Removed **GET** `/dlog/newdrivers`  
2. Removed `sort_by_highest_role` parameter from **GET** `/members`  
3. Added `order`, `order_by` parameter for **GET** `/members`, **GET** `/users`  
4. Added `order` parameter for **GET** `/dlogs`, **GET** `/applications`, **GET** `/announcements`  

## v1.10.6
  
1. Added support to email & password login  
2. Added time-range query for `/dlog/stats`  
3. Added more data for `/dlog/stats` response  

## v1.10.5
  
1. Removed `staff_of_the_month` and `drivers_of_the_month`  
2. Added `roles` and `sort_by_highest_role` parameter for **GET** `/members`  
3. Added tracker reload when reloading service  
4. Added information and copyright in tracker  

## v1.10.4
  
1. Added data compression for `dlog.detail` and `application.detail`  
2. Added upgrade plugin  
3. Added `version` in database settings table  

## v1.10.3
  
1. Fixed [admin.py](/src/apis/admin.py) bug overwriting original `tconfig` which causes 500 on **GET** `/admin/config`  
2. Improved driver & staff of the month and division role detection by adding ',' at the start and end of `roles` column  

## v1.10.2
  
1. Fixed minor bugs  
2. Added `pagelimit` parameter for all list response  

## v1.10.1
  
1. Config format update (Use `config_upgrade.py` in release to upgrade config to v1.10.1)  
a) Item name changes  
|Old Name|New Name|  
---|---|  
|vtcprefix|vtc_abbr|  
|vtcname|vtc_name|  
|hexcolor|hex_color|  
|vtclogo|vtc_logo_link|  
|teamupdate|team_update_image_link|  
|domain|apidomain|  
|dhdomain|domain|  
|guild|guild_id|  
|navio_token|navio_api_token|  
|delivery_gifs|delivery_post_gifs|  
|bot_token|discord_bot_token|  
|team_update_message|webhook_teamupdate_message|  
|driver_channel_id|welcome_channel_id|  
|welcome_image|welcome_image_link|  
|welcome_roles|welcome_role_change|  
|division_manager_role|webhook_division_message|  
|divisions[].roleid|division[].role_id|  

b) Removed `public_news_role` and `private_news_role` in config, merged them to `discord_message_content` which will be provided in form  
c) Merged `ranking` and `rankname` to `ranks = [{"distance": 0, "name": "", "role_id": 0}]`  
d) Changes on application system  
i) Removed `assign_application_role`, `applicant_driver`, `applicant_staff`, `loa_request`, `human_resources_role`  
ii) Created `application_types` (`role_id` is role to assign to applicant, `message` is content of webhook message)  
iii) id = 1~4 are reserved for special use and must not be changed  
e) Added `downloads` to `config.permission`  
f) Changed all `int` to `str` to prevent precision lose  
2. Changed **GET** `/token` response `extra` to `note`  
3. Removed `driver_of_the_day` from **GET** `/dlog/stats` (use leaderboard instead)  
4. Changed all `int` response element to `str`  
5. Changed **GET** `/dlog` response `data` to `detail`  
6. Changed **GET** `/dlog/chart` `addup` parameter to `sum`  
7. Changed **GET** `/application` response `data` to `detail`  

## v1.9.12
  
1. Added `expense`, `net_profit` column in exported .csv table  
2. Updated delivery webhook post  

## v1.9.11
  
Added zlib compression for telemetry data (saving ~40% storage)  

## v1.9.10
  
1. Changed `config.telemetry_innodb_dir` to `mysql_ext`  
2. Moved `announcement`, `dlog`, `division`, `event`, `application`, `auditlog`, `downloads` TABLE to `mysql_ext` for external storage  

**A method to move data directory**  
ALTER TABLE `table` RENAME TO `table_old`;  
CREATE TABLE IF NOT EXISTS `table` `schema` DATA DIRECTORY = '/.../';  
INSERT INTO `table` SELECT * FROM `table_old`;  
DROP TABLE `table_old`;  

## v1.9.9
  
1. Fixed the bug that User ID replaced User Name on `/dlog`  
2. Updated telemetry data encoding method  

## v1.9.8
  
1. Updated IP check mechanism  
2. Allowed admin roles to be updated with API  
3. Added response status code to all error response  
4. Improved fault-tolerance (hexcolor) for config

## v1.9.7
  
Added `config.perms.hrm` who has higher permission than `config.perms.hr`  

## v1.9.6
  
Added `config.perms.announcement` for announcement permission control  

## v1.9.5
  
Added `limituser` argument for `/dlog/leaderboard`  

## v1.9.4
  
1. Fixed the issue that delivery webhook post would fail when `config.delivery_gifs = []`  
2. Added audit log for **PATCH** `/config` and **PATCH** `/downloads`  
3. Added `config.steam_callback_url` to redirect to custom frontend page  
4. Changed to use official TruckersMP API to get TruckersMP ID with Steam ID  
5. Changed query parameter from `search` to `query` for **GET** `/members`  
6. Updated endpoint path (details in table below)  
7. Improved fault-tolerance (integer / string) for config (except `config.perms`)  
8. Improved and simplified code structure by using authentication API (in [functions.py](/src/functions.py))  
|Endpoint Name|Old Path|New Path|  
---|---|---|
|Validate token|**GET** `/user/validate`|**GET** `/token`  
|Request new token|**GET** `/user/refresh`|**PATCH** `/token`  
|Revoke token|**POST** `/user/revoke`|**DELETE** `/token`  
|Reset application token|**POST** `/user/apptoken`|**PATCH** `/token/application`  
|Redirect to Steam OAuth|**GET** `/user/steamauth`|**GET** `/user/steam/oauth`  
|Steam OAuth callback|**GET** `/user/steamcallback`|**GET** `/user/steam/callback`  
|Validate Steam OAuth (connect Steam account)|**POST** `/user/steambind`|**PATCH** `/user/steam`  
|Validate TruckersMP account (connect TruckersMP account)|**POST** `/user/truckersmpbind`|**PATCH** `/user/truckersmp`  
|Get delivery logs|**GET** `/dlog/list`|**GET** `/dlogs`  
|Get delivery log detail|**GET** `/dlog/detail`|**GET** `/dlog`  
|Get members|**GET** `/member/list`|**GET** `/members`  
|Get member detail|**GET** `/member/info`|**GET** `/member`  
|Update rank role|**PATCH** `/member/discordrole`|**PATCH** `/member/role/rank`  
|Get users|**GET** `/user/list`|**GET** `/users`  
|Get user details|**GET** `/user/info`|**GET** `/user`  
|Get applications|**GET** `/application/list`|**GET** `/applications`  
|Get divisions|**GET** `/division/list`|**GET** `/divisions`  
|Get pending division validation|**GET** `/division/validate`|**GET** `/divisions/pending`  
|Get division detail|**GET** `/division/info`|**GET** `/division`  
|Request division validation|**POST** `/division/validate`|**POST** `/division`  
|Update division validation|**PATCH** `/division/validate`|**PATCH** `/division`  
|Get all events|**GET** `/event/full`|**GET** `/events/all`  

## v1.9.3
  
1. Added **PATCH** `/user/unbind` endpoint to unbind connections  
2. Added **DELETE** `/user/delete` endpoint to delete user  
3. Added **GET** `/dlog/export` endpoint to export .csv table of deliveries  
4. Added auto remove for expired ratelimit data  
5. Removed error response code for non 401 or 429 errors  

## v1.9.2
  
1. Fixed bugs with role detection  
2. Updated driver detection mechanism for application  

## v1.9.1
  
1. Added Rate Limiter  
2. Added response status code for 401 and 404 errors  
3. Updated delivery webhook post  
4. Allowed application token for **GET** `/downloads`  

## v1.8.13
  
1. Removed function to not create database table for disabled plugins  
2. Updated delivery webhook post  

## v1.8.12
  
Fixed bug of navio webhook not accepting WoT jobs due to non-int meta distance  

## v1.8.11
  
Fixed bug of `welcome_roles` failing to remove roles  

## v1.8.10
  
1. Improved Discord OAuth2 Login  
2. Removed `/ip` endpoint  
3. Changed `/info` endpoint path to `/`  

## v1.8.9

1. Removed `intcolor` from `config.json` and calculate it with `hexcolor` on start  
2. Removed `/version` endpoint and improved `/info` endpoint  
3. Added admin endpoint to change user Discord ID (`/user/discord`)  
4. Added adminid (responsible user) & opquery (operation) filter for `/auditlog`  
5. Added profit for member profile  
6. Combined `europrofit` and `dollarprofit` to `profit` (dict) for `/dlog/stats` and `/dlog/chart`  
7. Improved `/dlog/stats` response data format  

- Launcher

1. Changed `RestartSec` to `60` when registering service  

## v1.8.8
  
Fixed Discord and Steam ID JSON precision lose  

## v1.8.7
  
1. Fixed [apis/navio](/src/apis/navio.py) `config.external_plugins` mistaked for `external_plugins`  
2. Fixed [apis/member](/src/apis/member.py) to use `distance` instead of `mile` for `/member/point` endpoint  
3. Added custom driver rank up message  
4. Added option to give / remove Discord roles for new members  

## v1.8.6
  
1. Added custom team update message, accept `{mention}` `{vtcname}` variable  
2. Added custom welcome message to be sent in drivers channel  
3. Added option to disable user in guild check  
4. Changed navio reject webhook responsible user to system  
5. Automated database settings nxt***id record creation  

## v1.8.5
  
1. Added option to remove TruckersMP Account requirement  
2. Fixed bug that translate function does not work with non-string variable  

## v1.8.4
  
1. Fixed bugs of config editing and improved data check  
2. Fixed bugs that delivery embed cannot be posted when *.name is none  

## v1.8.3
  
Fixed bugs of config editing  

## v1.8.2
  
1. Fixed bug allowing user to edit `telemetry_innodb_dir` and `language_dir` from API  
2. Added Spanish and French translation  

## v1.8.1
  
1. Supported multiple language  
2. Improved division to support certain point for each division  
3. Removed remaining VTC-specific functions  

## v1.7.4
  
1. Added telemetry_innodb_dir config option to store telemetry table on external storage  
2. Bug fixes  

**How to enable external innodb directory in MySQL?**  
(Suppose the directory is `/var/lib/mysqlext`)  

1. Create directory, change permission
   > chown mysql:mysql /var/lib/mysqlext

2. Open `/etc/mysql/mysql.conf.d/mysqld.cnf` and add
   > innodb_directories = /var/lib/mysqlext/ # this adds the directory to known innodb directory
   > secure-file-priv = /var/lib/mysqlext/ # this allows non-root user to create table with DATA DIRECTORY

3. Grant `FILE` privilege to the database user (which does not seem to be included in `ALL` privileges).

4. Reload mysqld: `systemctl restart mysql`

5. Open `/etc/apparmor.d/usr.sbin.mysqld` and add
    > /var/lib/mysqlext/ r,
    > /var/lib/mysqlext/** rwk,

6. Reload apparmor: `service apparmor reload`

## v1.7.3
  
1. Added permission control for audit log  
2. Removed non-driver (but member) from leaderboard  

## v1.7.2
  
Initial release after combing all hubs into one code  
