import sqlite3
import requests
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()

class TrueLayerHandler:
    def __init__(self, IP):
        self.ip = IP

        self.access_token = None
        self.refresh_token = None


        self.client_id = os.getenv('TRUELAYER_CLIENT_ID')
        self.client_secret = os.getenv('TRUELAYER_CLIENT_SECRET')
        self.redirect_uri = os.getenv('TRUELAYER_REDIRECT_URI')

        self.base_url = "https://api.truelayer.com/"
        self.urls = {
            'token': "https://auth.truelayer.com/connect/token",
            'accounts': 'data/v1/accounts'
            }

        self.urls['transactions'] = lambda account_id : f'{self.urls["accounts"]}/{account_id}/transactions'

    def authLinkBuilder(self):
        return "https://auth.truelayer.com/?response_type=code&client_id=jackbird-64e668&scope=info%20accounts%20balance%20cards%20transactions%20direct_debits%20standing_orders%20offline_access&redirect_uri=https://console.truelayer.com/redirect-page&providers=uk-ob-all%20uk-oauth-all"

    def authSetup(self, exCode):
        url = self.urls['token']

        payload = {
            "grant_type": "authorization_code",
            "client_id": f"{self.client_id}",
            "client_secret": f"{self.client_secret}",
            "redirect_uri": f"{self.redirect_uri}",
            "code": f"{exCode}"
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            response = response.json()
            self.access_token = response['access_token']
            self.refresh_token = response['refresh_token']

    def refreshAccessToken(self):
        url = self.urls['token']

        payload = {
            "grant_type": "refresh_token",
            "client_id": f"{self.client_id}",
            "client_secret": f"{self.client_secret}",
            "refresh_token": f"{self.refresh_token}",
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            response = response.json()
            self.access_token = response['access_token']
            self.refresh_token = response['refresh_token']

    def requestAccounts(self):
        url = f"{self.base_url}{self.urls['accounts']}"

        headers = {
            "Accept": "application/json",
            "X-Client-Correlation-Id": f"{self.client_id}",
            "X-PSU-IP": f"{self.ip}",
            "Authorization": f"Bearer {self.access_token}"
        }

        return requests.get(url, headers=headers)

    def requestTransactions(self, account_id, date_from=None, date_to=None):
        url = f"{self.base_url}{self.urls['transactions'](account_id)}"
        if date_from and date_to:
            url += f"?from={date_from}&to={date_to}"

        headers = {
            "Accept": "application/json",
            "X-Client-Correlation-Id": f"{self.client_id}",
            "X-PSU-IP": f"{self.ip}",
            "Authorization": f"Bearer {self.access_token}"
        }

        return requests.get(url, headers=headers)

    def requestResults(self, results_url):
        time.sleep(1)
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
            }
        return requests.get(results_url, headers=headers)

    def makeRequest(self, request, *args, called=1, **kwargs):
        print('called', called)
        print('args', args)
        called += 1
        if called > 3: 
            return "Too many errors"

        response = request(*args, **kwargs)

        if response.status_code == 202:
            if 'results_uri' in response.json():
                redirect = response.json()['results_uri']
                return self.makeRequest(self.requestResults, redirect)
            return response

        if response.status_code == 401:
            self.refreshAccessToken()
            return self.makeRequest(request, called=called, *args, **kwargs)

        return response

