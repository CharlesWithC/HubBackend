# Changelog

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
