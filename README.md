# Drivers Hub: Backend

Author: [@CharlesWithC](https://charlws.com)  
External plugins are supported, add files to `/src/external_plugins` and edit config, then they'll be loaded without the need to compile again!

**Main features:**  
1.Discord OAuth2 Login + Steam & TruckersMP Account Connection  
2.Delivery log and telemetry tracker  
3.Role-based permission management  
4.Multiple languages  
5.Editable config  

**Main plugins:**  
1.Announcement  
2.Application  
3.Division  
4.Downloads  
5.Event  

**Internal API**  
1.Authorization  
`auth(authorization, request, check_ip_address = True, allow_application_token = False, check_member = True, required_permission = ["admin", "driver"])`  
returns `{error: bool, discordid: int, userid: int, name: str, roles: list, application_token: bool}`  
2.Rate limit  
`ratelimit(ip, endpoint, limittime, limitcnt)`  
returns `rate_limit_timeout: int`  
