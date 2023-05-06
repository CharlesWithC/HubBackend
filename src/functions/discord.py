# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json

from functions.arequests import arequests


class DiscordAuth:
    def __init__(self, client_id, client_secret, callback_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url

    async def get_tokens(self, code):
        """ Gets the access token from the code given. The code can only be used on an active url (callback url) meaning you can only use the code once. """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.callback_url
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        resp = await arequests.post(None, 'https://discord.com/api/v10/oauth2/token', data=data, headers=headers)
        return json.loads(resp.text)
    
    async def refresh_token(self, refresh_token):
        """ Refreshes access token and access tokens and will return a new set of tokens """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        resp = await arequests.post(None, 'https://discord.com/api/v10/oauth2/token', data=data, headers=headers)
        return json.loads(resp.text)


    async def get_user_data_from_token(self, access_token):
        """ Gets the user data from an access_token """
        headers = {
            "Authorization": f'Bearer {access_token}'
        }

        resp = await arequests.get(None, 'https://discord.com/api/v10/users/@me', headers=headers)
        return json.loads(resp.text)