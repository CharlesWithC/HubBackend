# Plugins

This is a brief introduction to plugins provided in this repo.

You may want to check:

- [/docs/config.jsonc](/docs/config.jsonc) for instructions on configuring the plugins
- [drivershub.charlws.com](https://drivershub.charlws.com/features) for brief demonstrations
- [wiki](https://github.com/CharlesWithC/HubWebsite/wiki) for some helpful information

## Announcement

A plugin for managing announcements.

Announcements may be forwarded to a Discord channel, based on the type and visibility of the announcement.

Announcements may be set to private or public. Private announcements may only be seen by accepted members. Public announcements may be seen by public users and when not logged in as well.

## Application

A plugin for submitting and managing applications.

Various conditions may be set for application submission.

Users may choose to receive notifications in Drivers Hub and Discord on application status update.

All submissions and communications may also be forwarded to a Discord channel for convenience.

Note that, the backend server only stores the metadata configuration for applications, and client may introduce different methods to build application forms. For example, [HubFrontend](https://github.com/CharlesWithC/HubFrontend) used a JSON-based application form configuration with various types of input fields and conditional fields.

Also, note that application status does not affect member status. Accepting an application does not automatically accept a user as member.

## Challenge

A plugin for driver challenges with automated completion check.

A very comprehensive list of conditions is supported. Typically, only a few are used for each challenge.

Challenges may be individual or collaborative, and may be based on number of jobs submitted or total distance covered.

All jobs submitted when a challenge is active are automatically checked against the challenge condition, and would contribute to challenge completion if all conditions are met. Jobs may also be manually validated for a challenge in case the automated system does not validate it.

A very complicated reward system was created to calculate the reward precisely and handle changes when jobs are validated/invalidated. Challenge points may be rewarded when a challenge is completed.

## Division

A plugin for division management with manual delivery validation.

Division membership is achieved by adding special division roles to users. A user may be in multiple divisions.

Users must submit job validations and have them manually validated by a staff member, in order for the job to count as a division job. Division points may be rewarded for validated division jobs, and such jobs count toward per-division statistics.

Note that this workflow was kept manual to mimic actual division workflow, allow comprehensive manual validations, and not overlap with the challenge plugin.

## Downloads

A plugin for managing downloadable items.

Downloadable items must be hosted externally, and the Drivers Hub will redirect users to the external URL when they request to download an item.

The external URL is protected and only revealed when the user is authenticated. Download counts are also available for each downloadable item.

## Economy

A plugin adding economy feature to the Drivers Hub.

The economy plugin is the most complicated plugin provided in the repo, as it creates a whole *virtual economy*. It is also the most autonomous plugin, as it does not follow the typical "staff create something, user see something" approach, and all data directly comes from in-game tracking (though special permissions exist that allow staff members to manage balance/trucks/garages in the economy).

Revenue from tracked jobs would be added to the player's bank balance in the economy system. And the player may purchase garages, trucks and merchandise (configured by the community) with virtual currency.

Trucks used in game are connected to trucks in the economy plugin based on truck `id`. Truck data such as odometer and damage would be synchronized cumulatively. If the player does not own a truck that is used in game, then the truck would be considered a rental and cost would be deducted from job revenue.

Garages are required to park all purchased trucks. Garages may be expanded (without limit) by purchasing additional parking slots.

A special account that represents the community exists in the economy system. This account can have a balance, and own trucks and garages. The balance in this account mainly comes from "company tax" (i.e. cut from player's revenue).

## Event

A plugin for managing events and event attendance.

Events may be forwarded to a Discord channel, and automated "upcoming event" reminders may be posted in a Discord channel as well.

Event attendance is managed manually and is used to reward event points to the attendees.

## Poll

A plugin for submitting and managing polls.

Staff members may create polls and all members may submit votes on polls.

Note that modifying poll choices is not allowed as one measure to ensure poll integrity.

## Task

A plugin for managing tasks.

All members may create tasks for themselves, and staff members may create tasks for other members.

Task completion may be validated by the task creator, and (regular) bonus points may be rewarded upon completion.
