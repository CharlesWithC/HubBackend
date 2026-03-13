# Guide

This is a basic guide explaining the general workflow of using the Drivers Hub.

Note that this article is agnostic to the client being used, as only the API's functionalities are assumed.

You may find some helpful information on [wiki.charlws.com](https://wiki.charlws.com/shelves/drivers-hub), though the wiki is likely outdated due to lack of maintenance.

## Configuration

The Drivers Hub must be properly configured before being released to a community.

This includes but is not limited to proper tracker integration, Discord integration, and SMTP configuration, if the features are being used.

If certain configuration is invalid, errors may occur preventing certain operations.

See [/docs/config.jsonc](/docs/config.jsonc) for a comprehensive documentation on the configuration.

## New User

Members of the community must create accounts on their own with a client, with email/password, Discord, or Steam. Staff members may not create accounts with any client since it is not supported by the API.

Duplicate accounts may be created, if the user signs up with multiple third-party accounts rather than connecting a third-party account to the Drivers Hub account. In such cases, the administrator may delete duplicate accounts.

All new users are considered "guest" / "public" users. They will have limited access to the Drivers Hub until they are accepted as a member by a staff member.

## Accepting Users

Staff members may accept a user and assign them roles with a client.

Once a user is an "accepted member", the user will be able to see all content that is limited to members.

Note that "member" is not equivalent to "driver". The Drivers Hub was designed so that non-driver users may be accepted as members, such as external staff members like developers. Drivers must be assigned a driver role (with "driver" permission), so that the driver status can be confirmed.

Also, note that, the application plugin is not related to "accepting users". Accepting an application only changes the status of the application, and does not change the status of a user.

## Tracking Jobs

The driver must have Steam account connected to the Drivers Hub account in order to track jobs, as all trackers use Steam ID to identify drivers.

If using supported third-party trackers, and the tracker is properly configured, then a member will be automatically added to the organization in the tracker platform when the driver role is added.

While multiple trackers may be used by the community, each driver must choose one tracker where data would be processed. Data from other trackers, if received, will be dropped. This prevents duplicate jobs from being processed.

Note that, the user must have "driver" role for the jobs to be processed. Otherwise, the data from trackers, if received, will be dropped.

## Do More with Plugins

A lot of interesting stuff can be done with plugins, such as challenges, divisions, economy and events.

See [/docs/plugins.md](/docs/plugins.md) for more information.
