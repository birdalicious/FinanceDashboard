import re
import requests
import time

def tlRequest(request):
    def inner(self, *args, called=1, **kwargs):
        called += 1
        if called > 3:
            return "Too many errors"

        response = request(self, *args, **kwargs)

        if response.status_code == 202:
            if 'results_uri' in response.json():
                url = response.json()['result_uri']
                return self.getResults(self, url)
            return response
        
        if response.status_code == 401:
            self.refreshAccessToken()
            return request(self, called=called, *args, **kwargs)

        return response

    return inner


class TrueLayerHandler:
    def __init__(self, client_id, client_secret, redirect_uri, IP, refresh_token=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.ip = IP

        self.access_token = None
        self.refresh_token = refresh_token

        if self.refresh_token:
            self.refreshAccessToken()


    def endpoint(self, type, key=None):
        base_url = "https://api.truelayer.com"

        types = {
            'accounts': 'data/v1/accounts',
            'cards': 'data/v1/cards',
            'auth': 'https://auth.truelayer.com/connect/token',
        }

        endpoints = {
            'transactions': lambda account_id: f"{account_id}/transactions",
            'pending': lambda account_id: f"{account_id}/transactions/pending",
            'balance': lambda account_id: f"{account_id}/balance",
            'standing_orders': lambda account_id: f"{account_id}/standing_orders",
            'direct_debits': lambda account_id: f"{account_id}/direct_debits",
        }

        if type == 'auth':
            return types['auth']

        url = f"{base_url}/{types[type]}"

        if key:
            return lambda x : f"{url}/{endpoints[key](x)}"

        return url


    @tlRequest
    def authSetup(self, exCode):
        url = self.endpoint('auth')

        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "code": exCode
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            res = response.json()
            self.access_token = res['access_token']
            self.refresh_token = res['refresh_token']

        return response

    @tlRequest
    def refreshAccessToken(self):
        url = self.endpoint('auth')

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            res = response.json()
            self.access_token = res['access_token']
            self.refresh_token = res['refresh_token']

        return response


    def baseGetRequest(self, url):
        headers = {
            "Accept": "application/json",
            "X-Client-Correlation-Id": self.client_id,
            "X-PSU-IP": self.ip,
            "Authorization": f"Bearer {self.access_token}"
        }

        return requests.get(url, headers=headers)

    @tlRequest
    def getResults(self, url):
        time.sleep(1)
        return self.baseGetRequest(url)

    @tlRequest
    def getAccounts(self):
        url = self.endpoint('accounts')
        return self.baseGetRequest(url)
    
    @tlRequest
    def getCards(self):
        url = self.endpoint('cards')
        return self.baseGetRequest(url)

    @tlRequest
    def getBalance(self, account_id, card=False):
        if card:
            url = self.endpoint('cards', 'balance')(account_id)
        else:
            url = self.endpoint('accounts', 'balance')(account_id)
        return self.baseGetRequest(url)