# Changelog

**v1.21.14**  
1.Fixed database connection issue caused by v1.21.13  
2.Fixed bug `navio_api_error` not declared  
3.Changed **PATCH** `/user/name` to **PATCH** `/user/profile`, added avatar update on **PATCH** `/user/profile`  
4.Improved code base  

**v1.21.13**  
Improved database connection management and reduced resource consumption  

**v1.21.12**  
1.Prevented crash on certain types of invalid config  
2.Fixed **GET** `/downloads/redirect` 500 error when downloadable item not found  
3.Other bug fixes and minor improvements  

**v1.21.11**  
Added `end_time` request param to **GET** `/dlog/statistics/chart`  

**v1.21.10**  
1.Fixed manually-added distance leading to inaccurate result of leaderboard division point  
2.Fixed challenge completed status not adding to personal one-time / recurring challenge  

**v1.21.9**  
Removed unncessary `convert_quotation` that led to `\'` visible by user  

**v1.21.8**  
1.Improved internal / external API handling to prevent 500 errors when request failed  
2.Added `config.member_leave` to automate Discord message & role updates when driver leaves  
3.Added automatic rank role removal when driver leaves  
*Note: "leave" is defined by either driver role is removed, driver resigns, or driver is dismissed.  

**v1.21.7**  
1.Fixed **POST** `/user/tip` 500 error  
2.Fixed **GET** `/division` returns incorrect data  
3.Endpoint Route & Methods: Updated for better readability  
|Old|New|  
--|--|
|**PUT** `/auth/tip`|**POST** `/user/tip`|  
|**PUT** `/user/notification/status`|**PATCH** `/user/notification/status`|  
|**PATCH** `/user/notification/{{notification_type}}/enable`|**POST** `/user/notification/{{notification_type}}/enable`|  
|**PATCH** `/user/notification/{{notification_type}}/disable`|**POST** `/user/notification/{{notification_type}}/disable`|  
|**PUT** `/event/vote`|**PATCH** `/event/vote`|  

**v1.21.6**  
1.Fixed the bug being unable to parse `204` response which led to errors  
2.Added numeric value check to prevent large value being rejected by database  
3.Updated database datatype (mainly `discordid` to `BIGINT UNSIGNED`)  
4.Changed `distance` in `config.ranks` to `points`  

**v1.21.5**  
**[BannerGen]**  
1.Prevented sending request to BannerGen when cache exists  
2.Improved avatar caching mechanism  
**[Minor changes]**  
1.User activity: Changed `user_{userid}` to `member_{userid}`  
2.Rate limit: Added `X-RateLimit-Reset` and `X-RateLimit-Reset-After` header for non-429 responses  
3.User: Added **PATCH** `/user/name` to update username to latest Discord user name / server nickname  
4.Event: Added `first_event_after` request param for better ordering  
5.Discord Integration: Added error notification when fails to update roles  
6.Discord Integration: Added `config.use_server_nickname`, if `true`, then use nickname in Discord server  
7.Configuration: Added config validator to use default value for missing fields  
8.Endpoint Route & Methods: Updated for better readability  
|Old|New|  
--|--|
|**PUT** `/reload`|**POST** `/reload`|
|**PUT** `/auth/tip`|**POST** `/user/tip`|
|**GET** `/auth/tip`|**GET** `/user/tip`|
|**PUT** `/auth/mfa`|**POST** `/user/mfa`|
|**DELETE** `/auth/mfa`|**DELETE** `/user/mfa`|
|**DELETE** `/member/resign`|**POST** `/member/resign`|
|**DELETE** `/member/dismiss`|**POST** `/member/dismiss`|

**v1.21.4**  
1.Improved Discord Notification to send batched embeds (less messages, more embeds)  
2.Added distance-based challenge  
3.Fixed various bugs of challenge plugin  

**v1.21.3**  
**[BannerGen]**  
1.Merged `ConsolaBold` with `SansSerif` to support a larger character set  
2.Added unicode normalization to remove decoration to make more characters drawable  
3.Added division text length limiter to prevent overflowing into logo image  
4.Increased precision of changing `username` and `highest role` font size to 1 (originally 5)  
5.Improved `highest role` positioning algorithm  
6.Optimization (avg. 98ms/banner, originally 460ms/banner)  
**[Bug fixes]**  
1.Fixed **PATCH** `/config` cannot update `config.language`  
2.*[User]* Fixed **GET** `/user` activity adding a trailing ")"  
**[Minor changes]**  
3.Added config keys sorter to better organize config file  
4.*[Member]* Added `already_have_discord_role` response for **PATCH** `/member/roles/rank` when member is under distance required by lowest rank  
5.*[Dlog]* Added `order_by` (`logid`, `max_speed`, `profit`, `fuel`, `distance`) request param to **GET** `/dlog/list`  
6.Added support to Discord API v10  

**v1.21.2**  
Improved **GET** `/dlog/statistics/chart`, removed `scale` param, added `ranges` and `interval` params for better customizability  

**v1.21.1**  
**[Bug fixes]**  
1.Fixed the bug that **PATCH** `/member/roles/rank` is always returning `discord_integrations_disabled` response  
**[Minor changes]**  
2.Changed `unauthorized` responses due to insufficient permission to `forbidden`  
3.Updated upgrader to require `upgrade` parameter in `sys.argv`  
4.Added `config.language` to set company language for delivery log embed (audit log will always be in English)  
5.Updated activity info to program-friendly (frontend need to be updated to parse it)  
6.*[Challenge]* Added notification when challenge reward points is updated  
**[Major changes]**  
7.*[Dlog]* Added endpoint to delete deivery log: **DELETE** `/dlog`  
8.*[User]* Added endpoint to set and get language: **GET**, **PATCH** `/user/language`  
9.Updated `ml.translate` to consider user language if set (if not, then fall back to `Accept-Language`)  
10.Added full multilang support for all notification  
11.Polished Discord Notification of Login & Application & Division (better using embed)  
12.Added per-function notification settings  
13.Added `multilang_helper` to better manage translations internally  

**v1.20.3**  
1.Fixed **GET** `/config` 500 error when content related to disabled plugins are not in config  
2.Fixed event notification sending more than one  
3.Made it possible to send event notification for delayed event  
4.Added translation for `Unknown Error`  
5.Enabled thread daemon to make shutdowns faster  

**v1.20.2**  
Fixed the bug that program cannot shut down fully  

**v1.20.1**  
**[Bug fixes]**  
1.*[Auth]* Fixed the bug that ban check is not performed on steam & password login  
2.*[Auth]* Fixed the bug that referrer check does not work  
**[Minor changes]**  
2.*[Auth]* Increased session life to 30 days  
3.*[Auth]* Increased max session count to 50  
4.*[Auth]* Removed endpoint **GET** `/token/all`, added endpoint **GET** `/token/list`  
5.*[Auth]* Added `country`, `user_agent` and `last_used_timestamp` to session table  
6.*[Auth]* Changed session IP check to country check  
7.*[Auth]* Added `last_used_before` request param to **DELETE** `/token/all`  
8.Added Discord Bot Token Validation to prevent invalid tokens from being used  
9.Added `config.allowed_navio_ips`  
**[Major changes]**  
10.Added translation for all endpoints (except Navio Webhook)  
11.Added Russian, Turkish and Italian translation  
12.Improved rate limit response  
13.Added user-controllable Discord Notification and removed `discord_bot_dm` from config  
i) Added endpoint **PATCH** `/user/notification/{str:notification_type}/enable`, **PATCH** `/user/notification/{str:notification_type}/disable`,   **GET** `/user/notification/settings`  
ii) Discord Notifications use the same content as Drivers Hub Notifications  
iii) Notifications are queued up to prevent Drivers Hub being rate limited by Discord API.  
iv) If Drivers Hub fails to send a DM, Discord Notification (including Event Notification) will be disabled.  
v) All previously enabled-by-default Discord DMs have been disabled. User will have to manually enable Discord Notification to make DMs work  

**v1.19.6**  
Hard-coded English String Table  

**v1.19.5**  
1.Fixed the bug that **GET** `/dlog/list` returns same delivery for multiple times due to challenge record  
2.Added `public_details` to **GET** `/challenge` and **GET** `/challenge/list`  

**v1.19.4**  
**[BanerGen]**  
1.Reduced workers to 1 worker  
2.Reduced resolution to 1700x300  
3.General improvements on output  
**[Bug fixes]**  
1.*[Auth]* Fixed the bug that users whose names contain `'` fail to register  
**[Minor changes]**  
2.*[Application]* Added `status` request param to **GET** `/application/list`  
3.Added item wrapper to **GET** `/announcement`, **GET** `/application`, **GET** `/challenge`, **GET** `/downloads`, **GET** `/event`, **GET** `/user`, **GET** `/dlog`  
4.Changed integar response to string response for **GET** `/member/perms`  
5.Loosened API rate limit  

**v1.19.3**  
*[Challenge]* Added new challenge type `Personal (Recurring)` (original `Personal` type renamed to `Personal (One-time)`), which supports single challenge being completed for multiple times and receiving multiple rewards  

**v1.19.2**  
1.Fixed the bug that `is_private` is not updated when **PATCH** `/announcement`  
2.Fixed **GET** `/dlog/list` and **GET** `/dlog/export` shows pending division info  
3.Added 150,000-character limit for config  

**v1.19.1**  
**[Minor changes]**  
1.*[Dlog]* Improved `dlog` to support empty delivery log data (detail)  
2.*[Auth]* Updated **GET** `/auth/discord/callback` and **GET** `/auth/steam/callback` **Referer Check** to only make sure the request is not direct  
3.*[Auth]* Added **Referer Check** to **GET** `/auth/steam/connect`  
4.*[Auth]* Added **In-guild Check** to **POST** `/auth/password` and **GET** `/auth/steam/callback`  
5.*[Auth]* Improved **In-guild Check** to return `must_join_discord` error when Discord API Response Code is `404`  
6.Added `X-Audit-Log-Reason` header when updating User Discord Roles through Discord API  
**[New features]**  
7.*[Member]* Added `Navio API Error` to response of **PATCH** `/member/roles` (e.g. Steam profile is not public)  
8.*[Member]* Added `last_seen` to `order` parameter of **GET** `/member/list` and `last_seen_after` parameter to **GET** `/member/list`  
**[Major changes]**  
9.*[Dlog]* Improved Delivery Log Export (Added many more details, including division & challenge)  
10.*[Downloads]* Reworked **downloads** plugin, added item-based management and downloads click count  
11.Added per-function (endpoint) permission control (Note that existing integrated permissions are not modified)  
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

12.Optimized database query  
|Endpoint|Note|
--|--|
|**GET** /dlog/list|Improved division & challenge query, added division & challenge name in response|
|**GET** /user/list|Improved banned info query|

**v1.18.3**  
1.Fixed **GET** `/challenge/list` param `must_have_completed` not working correctly  
2.Changed order of `challenge[].completed` to `points DESC, timestamp ASC, userid ASC`  

**v1.18.2**  
1.*[Event]* Separated single-event query from event-list query  
2.*[Announcement]* Separated single-announcement query from announcement-list query  
3.*[User]* Changed **PUT** `/user/unban` to **DELETE** `/user/ban`  
4.*[User]* Changed `ban.ban_reason` response to `ban.reason`  
5.*[Challenge]* Added `completed` field in **GET** `/challenge` response  
6.*[Challenge]* Fixed various bugs of this plugin  
7.Added form string length limit  

**v1.18.1**  
**[Minor changes]**  
1.*[Challenge]* Added multiple item support to `source_city_id`, `source_company_id`, `destination_city_id`, `destination_company_it`, `cargo_id`  
**[New features]**  
2.Added user activity  
3.Added notification system  

**v1.17.1**  
**[Bug fixes]**  
1.*[Member]* Fixed **PATCH** `/member/roles/rank` giving highest role when there is no `point = 0` role  
**[Minor changes]**  
2.*[Member]* Added automatic redirect for `/member/banner` to `?userid=` when query param is not `userid`  
3.*[Announcement]* Added `order_by` (`announcementid` or `title`) and `title` (for searching) parameter to **GET** `/announcement`  
4.*[Division]* Moved `divisionid` to request param instead of form data for **POST** `/division`, **PATCH** `/division`  
5.*[Division]* Added `page`, `page_size`, `divisionid` parameter to **GET** `/division/list/pending`  
6.*[Division]* Added division info to **GET** `/dlog`  
7.*[Division]* Added detailed division info to **GET** `/dlog/list`, removed `division_validated` field  
8.*[Division]* Added `division` request param to `/dlog/list` to query division delivery, removed `recent_deliveries` from **GET** `/division`  
9.*[Event]* Added `title` (for searching) parameter to **GET** `/event`  
10.Improved audit log  
**[New features]**  
11.*[User]* Updated **DELETE** `/user`, moved `discordid` to request params. If specified, then delete user with the Discord ID. Otherwise delete user themselves. This will not delete a member  
12.*[Config]* Added `config.delivery_rules` with `max_profit`, `max_speed`, `action` sub-keys. `action` could be `block`, `drop`, `bypass`. `block` will reject the delivery from webhook post, `drop` will drop the item that violated the rule, `bypass` will accept the delivery (or, disable the rules). `drop` will only work for `max_profit`, by reducing it to `0`.  
13.*[Challenge]* Added new plugin: **challenge**  
**[Database Changes]**  
1.*[Announcement]* Plain text for `title` and compressed `content`  
2.*[Division]* Compressed `message`  
3.*[Downloads]* Compressed `downloads`  
4.*[Event]* Plain text for `title`, `departure`, `destination` and compressed `link`, `description`  

**v1.16.1**  
1.Fixed application setting `user[userid=0]` as `last_update_staff` when nobody updated the application  
2.Fixed config update corruption due to multiple workers  
3.Fixed **PATCH** `/user/discord` that removes account when `old_discord_id = new_discord_id`  
4.Fixed **PUT** `/user/ban` always using "Unknown User" in audit log  
5.Removed `bot_application_received` message  
6.Removed **PUT** `/config/reset` endpoint  
7.Added MFA support to **PATCH**, **DELETE** `/token/application`, **DELETE** `/user/password`  
8.Tightened rate-limit of **GET** `/member/banner` to 2r/10s (from 30r/180s), also lowered `bannergen` workers to 3  
9.Improved rate-limiter, added 10-minute ban for IPs surpassing 150r/m  

**v1.15.11**  
1.Removed detailed per-user statistics from **GET** `/division`  
2.Updated **GET** `/dlog/leaderboard` response to include `total` and `rank` in `points`  
3.Improved **PATCH** `/division` to prevent overwriting `divisionid` to invalid id  
4.Added 100-row limit to **GET** `/division/list/pending` to prevent large response  

**v1.15.10**  
1.Fixed speed limit not working for `/dlog/list` and `/dlog/leaderboard`  
2.Added `status` parameter `(0: All | 1: Delivered | 2: Cancelled)` to `/dlog/list`  
3.Added `status` field to `/dlog/list` response  

**v1.15.9**  
1.Fixed announcement plugin 500 error  
2.Added avatar to announcement and audit log embed  

**v1.15.8**  
Moved Steam & TruckersMP connection check to when adding driver role instead of when accepting user as member  

**v1.15.7**  
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

**v1.15.6**  
1.Improved TOTP function to accept OTP of bigger time range  
2.Added MFA secret base32 check  
3.Added MFA support (if enabled) to **PATCH** `/user/password`  

**v1.15.5**  
Fixed leaderboard skipping rank due to deleted users  

**v1.15.4**  
Fixed **GET** `/config` returning malformed `roles` data  

**v1.15.3**  
Fixed bannergen showing username as company name  

**v1.15.2**  
1.Fixed **POST** `/reload` 500 error when MFA is not enabled  
2.Changed `tip` form field to `token` for **POST** `/auth/mfa`  

**v1.15.1**  
Added **Multiple Factor Authentication**  
i) New endpoints: **PUT**, **POST**, **DELETE** `/auth/mfa`  
ii) Endpoint to check if user has MFA enabled: **GET** `/user`  
iii) Endpoints that support MFA if enabled: **POST** `/auth/password`, **GET** `/auth/discord/callback`, **GET** `/auth/steam/callback`, **DELETE** `/member/resign`  
iv) Endpoint that requires MFA: **POST** `/reload`  

**v1.14.5**  
1.Removed 'vtc' element  
2.Added `points` field to **GET** `/event` response  
3.Added `config.discord_bot_dm` (boolean) to enable / disable bot DM  
4.Config format update  
a) Item name changes  
|Old Name|New Name|  
---|---|  
|vtc_abbr|abbr|
|vtc_name|name|
|vtc_logo_link|logo_url|  

b) Updated `roles` format to `[{"id": "id", "name": "role"}]`  

**v1.14.4**  
1.Fixed `isdivision` (boolean) response being stringified to "True" / "False"  
2.Added `Unknown Error` response to **GET** `/auth/discord/callback` to prevent `Internal Server Error`  
3.Added `name` parameter to **GET** `/user/list` request for querying username  
4.Added User ID to application messages  
5.Added `backup` field to **GET** `/config` response for getting old config (currently loaded) before reload  
6.Added endpoint **PUT** `/config/reset` to revert config to old config (currently loaded)  
7.Added `frontend_urls` to config to customize frontend URL on redirect / clickable link  
8.Updated partial string table items  
9.Updated `images` for events to `description`  
10.Renamed database columns for better readability  
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

**v1.14.3**  
Improved role & config update validator to prevent admin users removing their own admin permission  

**v1.14.2**  
Added steam login  

**v1.14.1**  
1.Improved config validation on **PATCH** `/config`  
2.Removed automatic reload on **PATCH** `/config`  
3.Added **Temporary Identity Proof** (`/auth/tip`)  

**v1.13.2**  
1.Added 400 response when required form data is not provided  
2.Added "real deletion" for `announcement` and `event` instead of changing the id to negative numbers  
3.Improved API Documentation  

**v1.13.1**  
1.Added ability to edit meta elements of automated embeds in Discord (Welcome, Team Update, Rank Update)  
2.Added ability to switch between webhook and bot for automated embeds in Discord (Welcome, Team Update, Rank Update)  
3.Updated partial endpoint path or method  

**v1.12.9**  
1.Fixed the bug that updating event point without updating attendee doesn't work  
2.Added **DELETE** `/user/password` endpoint and removed the ability to disable password login by passing empty password to **PATCH** `/user/password`  

**v1.12.8**  
1.Fixed 500 error when submitting division validation request  
2.Fixed 500 error when Drivers Hub gets error from Discord getting user data (`/auth/discord/callback`)  
3.Fixed some 500 errors when trying to convert non-int to int  

**v1.12.7**  
Improved endpoint path and response format for better readability

**v1.12.6**  
Improved Banner Generator:  
i) Fixed 500 error when image is invalid  
ii) Fixed transparent logo background becoming solid in some cases  
iii) Improved rounded avatar generation and added transparency  

**v1.12.5**  
1.Fixed 500 error on `/user` when `config.privacy = false` and no authorization header is provided  
2.Fixed `/member/steam` showing non-member information  

**v1.12.4**  
1.Fixed 500 error on `/dlog/stats` when `config.privacy = true`  
2.Added Discord Login requirement to `/user/discord`, `/user/connection`, `/user/delete`, `/member/dismiss`, `/member/resign`  
3.Reduced cache expire time from 300 seconds to 120 seconds for `/dlog/stats` and `/dlog/leaderboard`  

**v1.12.3**  
Improved leaderboard ordering  

**v1.12.2**  
1.Added cache for `/dlog/stats` (5min), `/dlog/leaderboard` (5min), `/user/banner` (1hr)  
2.Removed statistics in `/user`  
3.Removed `driver` table  
4.Improved database index creation  
5.Fixed some bugs  

**v1.12.1**  
1.Added Myth Point  
2.Changed getting `distance` and `eventpnt` from `driver` table to calculating them with record  
3.Recoded `/dlog/leaderboard`  
4.Fixed some bugs  

**v1.11.5**  
1.Fixed the bug that leaderboard is not loading  
2.Improved authentication system  
3.Removed possibility to add event point and division point using `/member/point`  
4.Added possibility of showing `distance` added with `Update Member Point` on time-ranged leaderboard  
5.Added `hr` permission to `/member/point`  

**v1.11.4**  
Improved Banner Generator to save memory  

**v1.11.3**  
1.Merged `/member` and `/user` to `/user` for both member and public user, added `discordid`, `steamid`, `truckersmpid` parameter  
2.Added `config.privacy` to select whether to show / hide member information in public, including: `/member/steam`, `/members`, `/user`, `/dlog`, `/dlogs`  
3.Added `userid` parameter to `/dlog/stats` to query detailed user statistics (require `config.privacy = false`)  
4.Added `/user/banner` for auto-generated profile banner (require `banner` in `config.enabled_plugins`)  
5.Updated ratelimit  
6.Updated API error response  

**v1.11.2**  
Added requirement to login with discord to revoke specific / all token  

**v1.11.1**  
1.Improved `application` plugin:  
i) Added support to per-type webhook  
ii) Added support to per-type staff role  
iii) Removed reservation for type ID 1~4 (driver, staff, loa, division)  
iv) Added `note` (`driver`) for `config.application_types` as a substitute of reservation  
2.Improved authentication  
i) Added **DELETE** `/token/all` endpoint to revoke all sessions  
ii) Added **DELETE** `/token/hash` endpoint to revoke specific token with sha256 hash  
iii) Added **GET** `/token/all` endpoint to get all token sha256 hash, ip and timestamp  
iv) Added session limit to ensure user have a maximum of 10 active sessions  

**v1.10.10**  
Added `revoke-all-token` when updating password  

**v1.10.9**  
Removed regex email validation  

**v1.10.8**  
Fixed the bug that application webhook contains words in applicant's language  

**v1.10.7**  
1.Removed **GET** `/dlog/newdrivers`  
2.Removed `sort_by_highest_role` parameter from **GET** `/members`  
3.Added `order`, `order_by` parameter for **GET** `/members`, **GET** `/users`  
4.Added `order` parameter for **GET** `/dlogs`, **GET** `/applications`, **GET** `/announcements`  

**v1.10.6**  
1.Added support to email & password login  
2.Added time-range query for `/dlog/stats`  
3.Added more data for `/dlog/stats` response  

**v1.10.5**  
1.Removed `staff_of_the_month` and `drivers_of_the_month`  
2.Added `roles` and `sort_by_highest_role` parameter for **GET** `/members`  
3.Added tracker reload when reloading service  
4.Added information and copyright in tracker  

**v1.10.4**  
1.Added data compression for `dlog.detail` and `application.detail`  
2.Added upgrade plugin  
3.Added `version` in database settings table  

**v1.10.3**  
1.Fixed [admin.py](/src/apis/admin.py) bug overwriting original `tconfig` which causes 500 on **GET** `/admin/config`  
2.Improved driver & staff of the month and division role detection by adding ',' at the start and end of `roles` column  

**v1.10.2**  
1.Fixed minor bugs  
2.Added `pagelimit` parameter for all list response  

**v1.10.1**  
1.Config format update (Use `config_upgrade.py` in release to upgrade config to v1.10.1)  
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

2.Changed **GET** `/token` response `extra` to `note`  
3.Removed `driver_of_the_day` from **GET** `/dlog/stats` (use leaderboard instead)  
4.Changed all `int` response element to `str`  
5.Changed **GET** `/dlog` response `data` to `detail`  
6.Changed **GET** `/dlog/chart` `addup` parameter to `sum`  
7.Changed **GET** `/application` response `data` to `detail`  

**v1.9.12**  
1.Added `expense`, `net_profit` column in exported .csv table  
2.Updated delivery webhook post  

**v1.9.11**  
Added zlib compression for telemetry data (saving ~40% storage)  

**v1.9.10**  
1.Changed `config.telemetry_innodb_dir` to `mysql_ext`  
2.Moved `announcement`, `dlog`, `division`, `event`, `application`, `auditlog`, `downloads` TABLE to `mysql_ext` for external storage  

**A method to move data directory**  
ALTER TABLE `table` RENAME TO `table_old`;  
CREATE TABLE IF NOT EXISTS `table` `schema` DATA DIRECTORY = '/.../';  
INSERT INTO `table` SELECT * FROM `table_old`;  
DROP TABLE `table_old`;  

**v1.9.9**  
1.Fixed the bug that User ID replaced User Name on `/dlog`  
2.Updated telemetry data encoding method  

**v1.9.8**  
1.Updated IP check mechanism  
2.Allowed admin roles to be updated with API  
3.Added response status code to all error response  
4.Improved fault-tolerance (hexcolor) for config

**v1.9.7**  
Added `config.perms.hrm` who has higher permission than `config.perms.hr`  

**v1.9.6**  
Added `config.perms.announcement` for announcement permission control  

**v1.9.5**  
Added `limituser` argument for `/dlog/leaderboard`  

**v1.9.4**  
1.Fixed the issue that delivery webhook post would fail when `config.delivery_gifs = []`  
2.Added audit log for **PATCH** `/config` and **PATCH** `/downloads`  
3.Added `config.steam_callback_url` to redirect to custom frontend page  
4.Changed to use official TruckersMP API to get TruckersMP ID with Steam ID  
5.Changed query parameter from `search` to `query` for **GET** `/members`  
6.Updated endpoint path (details in table below)  
7.Improved fault-tolerance (integar / string) for config (except `config.perms`)  
8.Improved and simplified code structure by using authentication API (in [functions.py](/src/functions.py))  
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

**v1.9.3**  
1.Added **PATCH** `/user/unbind` endpoint to unbind connections  
2.Added **DELETE** `/user/delete` endpoint to delete user  
3.Added **GET** `/dlog/export` endpoint to export .csv table of deliveries  
4.Added auto remove for expired ratelimit data  
5.Removed error response code for non 401 or 429 errors  

**v1.9.2**  
1.Fixed bugs with role detection  
2.Updated driver detection mechanism for application  

**v1.9.1**  
1.Added Rate Limiter  
2.Added response status code for 401 and 404 errors  
3.Updated delivery webhook post  
4.Allowed application token for **GET** `/downloads`  

**v1.8.13**  
1.Removed function to not create database table for disabled plugins  
2.Updated delivery webhook post  

**v1.8.12**  
Fixed bug of navio webhook not accepting WoT jobs due to non-int meta distance  

**v1.8.11**  
Fixed bug of `welcome_roles` failing to remove roles  

**v1.8.10**  
1.Improved Discord OAuth2 Login  
2.Removed `/ip` endpoint  
3.Changed `/info` endpoint path to `/`  

**v1.8.9**  
**API**  
1.Removed `intcolor` from `config.json` and calculate it with `hexcolor` on start  
2.Removed `/version` endpoint and improved `/info` endpoint  
3.Added admin endpoint to change user Discord ID (`/user/discord`)  
4.Added adminid (responsible user) & opquery (operation) filter for `/auditlog`  
5.Added profit for member profile  
6.Combined `europrofit` and `dollarprofit` to `profit` (dict) for `/dlog/stats` and `/dlog/chart`  
7.Improved `/dlog/stats` response data format  
**Launcher**  
Changed `RestartSec` to `60` when registering service  

**v1.8.8**  
Fixed Discord and Steam ID JSON precision lose  

**v1.8.7**  
1.Fixed [apis/navio](/src/apis/navio.py) `config.external_plugins` mistaked for `external_plugins`  
2.Fixed [apis/member](/src/apis/member.py) to use `distance` instead of `mile` for `/member/point` endpoint  
3.Added custom driver rank up message  
4.Added option to give / remove Discord roles for new members  

**v1.8.6**  
1.Added custom team update message, accept `{mention}` `{vtcname}` variable  
2.Added custom welcome message to be sent in drivers channel  
3.Added option to disable user in guild check  
4.Changed navio reject webhook responsible user to system  
5.Automated database settings nxt***id record creation  

**v1.8.5**  
1.Added option to remove TruckersMP Account requirement  
2.Fixed bug that translate function does not work with non-string variable  

**v1.8.4**  
1.Fixed bugs of config editing and improved data check  
2.Fixed bugs that delivery embed cannot be posted when *.name is none  

**v1.8.3**  
Fixed bugs of config editing  

**v1.8.2**  
1.Fixed bug allowing user to edit `telemetry_innodb_dir` and `language_dir` from API  
2.Added Spanish and French translation  

**v1.8.1**  
1.Supported multiple language  
2.Improved division to support certain point for each division  
3.Removed remaining VTC-specific functions  

**v1.7.4**  
1.Added telemetry_innodb_dir config option to store telemetry table on external storage  
2.Bug fixes  

**How to enable external innodb directory on MySQL?**  
(Suppose the directory is `/var/lib/mysqlext`)  

0.Create directory, change permission
> chown mysql:mysql /var/lib/mysqlext  

1.Open `/etc/mysql/mysql.conf.d/mysqld.cnf` and add  
> innodb_directories = /var/lib/mysqlext/ # this adds the directory to known innodb directory  
  secure-file-priv = /var/lib/mysqlext/ # this allows non-root user to create table with DATA DIRECTORY

2.Grant `FILE` privilege to database user (which does not seems to be included in `ALL` privileges)

3.Reload mysqld: `systemctl restart mysql`  

4.Open `/etc/apparmor.d/usr.sbin.mysqld` and add  
> /var/lib/mysqlext/ r,  
  /var/lib/mysqlext/** rwk,
  
5.Reload apparmor: `service apparmor reload`  

**v1.7.3**  
1.Added permission control for audit log  
2.Removed non-driver (but member) from leaderboard  

**v1.7.2**  
Initial release after combing all hubs into one code  
