# Drivers Hub: Backend

Author: [@CharlesWithC](https://charlws.com)  

**Features:**  
1.Discord OAuth2 Login + Steam & TruckersMP Account Connection  
2.Delivery log and telemetry tracker  
3.Role-based permission management  
4.Multiple languages  
5.Editable config  
6.Plugin system: Official and external. Official plugins are compiled into executive files, and external plugins can be loaded directly without the need to recompile the source code!  

**Official Plugins**  
Announcement, Application, Division, Downloads, Event  

**Code API**  
1.Authorization  
`auth(authorization, request, check_ip_address = True, allow_application_token = False, check_member = True, required_permission = ["admin", "driver"])`  
returns `{error: bool, discordid: int, userid: int, name: str, roles: list, application_token: bool}`  
2.Rate limit  
`ratelimit(ip, endpoint, limittime, limitcnt)`  
returns `rate_limit_timeout: int`  
