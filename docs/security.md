# Security Features

The drivers hub has several built-in security features, including custom authentication, permission control and rate limiting mechanisms.

## Authentication

All authentication uses the `Authorization: {token}` header. All tokens are UUIDs stored in the database with no data encoded, and thus may be revoked upon request.

There are two types of tokens: `Bearer` and `Application`. `Bearer` tokens are for regular users and acquired through the login process. `Application` tokens are for applications and have some limitations for security reasons, and may be requested by regular users.

Endpoints that require authentication typically involve permission control as well, which includes member status validation (i.e. whether the user is an accepted member or a public user), and role validation (i.e. whether the user has roles that grant them the necessary permission). Role validation may involve multiple permissions, and passing the validation requires the user to have at least one role that grants them at least one of the involved permissions.

To improve performance, tokens are cached in redis for 60 seconds to reduce the number of database queries. All cache expires in 60 seconds and is not renewed - when a cache-miss occurs, a database query will be triggered to revaliate the token (renewing the cache indefinitely may lead to strange issues such as token becoming non-revokable). When a token is revoked, the cached token would be immediately deleted.

Enhanced security is supported though typically disabled. This involves IP block and country validation. The feature was initially added to protect the user against a token leak, i.e. if a token is leaked and accessed from a different location, then it would be automatically revoked. See attribute `security_level` in [/docs/config.jsonc](/docs/config.jsonc) for more information. Note that enhanced security is always disabled for application tokens.

## Rate Limit

All requests are subject to rate limiting.

There are two types of rate limits: `global` and `local`. `global` rate limit is based on the total number of requests for all endpoints. `local` rate limit is based on the number of requests for a specific endpoint.

`global` rate limit allows up to 300 requests in a 60-second period. Exceeding that would result in a global rate limit, where the user may not access any endpoints for 5 minutes.

`local` rate limit differs by endpoint, and the limit is typically related to how resource-intensive the request is, as well as how many external api calls would be made per request, but sometimes it is set relatively subjectively (such as, limiting the number of members that can be accepted in one minute, so that members cannot be mass-accepted).

When an authentication token is provided, it would be validated against the cache, and if the token is present in the cache, then the rate limit would be tied to the specific user. Otherwise, the rate limit would apply to the IP where the request originates. Note that, as long as the token is not present in the cache, even if it may be valid, the IP would be used as the identifier for rate limiting purpose.

All data for rate limiting is stored in redis, and never stored in the persistent database. This ensures high performance on rate limit handling, allows the data to be shared across worker processes, and prevents the database from being overloaded in the case of an attack.

It is still recommended to implement a global rate limit at reverse-proxy level, since reverse proxies are typically more efficient in handling requests at a high level.

## Extra

TOTP-based Multi-Factor Authentication (MFA) is supported. If a user enables MFA, then the One Time Passcode (OTP) would be required at every login, for all login methods.

If a user has permission to reload configuration, then the user must enable MFA before performing the action, since reloading configuration may lead to destructive behaviors (i.e. the old configuration would be overwritten and may not be reverted). Note that, the user does not need to enter OTP when saving configuration, since saving configuration creates a copy of the old configuration which is revertable, and the saved configuration is not applied before being reloaded.

Captcha is required for password-based logins to prevent bots and brute-force attacks (even though the rate limiting mechanism should block such attempts). hCaptcha and CloudFlare Turnstile are supported.
