import os
import requests
from datetime import date, datetime, timedelta

from database import DatabaseHandler
from truelayer import TrueLayerHandler

from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("TRUELAYER_CLIENT_ID")
CLIENT_SECRET = os.getenv("TRUELAYER_CLIENT_SECRET")
REDIRECT_URI = os.getenv("TRUELAYER_REDIRECT_URI")

class DataMarshaller:
    def __init__(self, dbHandler, ip=None):
        self.ip = ip if ip else self.getIP()
        self.db = dbHandler

        self.tlHandlers = {}
        self.accounts = {}
        self.accountToLink = {}

    def getIP(self):
        return requests.get('https://api.ipify.org').content.decode('utf8')


    def loadAccounts(self):
        for link_id, refresh_token in self.db.getRefreshTokens():
            tlHandler = TrueLayerHandler(
                CLIENT_ID,
                CLIENT_SECRET,
                REDIRECT_URI,
                self.ip, 
                refresh_token=refresh_token
            )

            self.tlHandlers[link_id] = tlHandler
            self.accounts[link_id] = set()

            for account in self.db.getAccounts(link_id=link_id):
                account_id = account['account_id']

                self.accounts[link_id].add(account_id)
                self.accountToLink[account_id] = link_id

    def refreshOverdraft(self, account_id):
        link_id = self.accountToLink[account_id]
        tlHandler = self.tlHandlers[link_id]

        overdraft = tlHandler.getBalance(account_id).json()['results'][0]['overdraft']
        self.db.setOverdraft(account_id, overdraft)

    def addAccounts(self, link_id):
        if self.db.getAccounts(link_id):
            return

        tlHander = self.tlHandlers[link_id]

        response = tlHander.getAccounts()
        if response.status_code != 200:
            return
        
        accounts = response.json()['results']
        for account in accounts:
            self.db.addAccount(link_id=link_id, **account)
            self.refreshOverdraft(accounts['account_id'])