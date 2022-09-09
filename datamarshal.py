from distutils.errors import LinkError
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
        self.cards = {}
        self.cardToLink = {}
        self.loadTLHandlers()

    def getIP(self):
        return requests.get('https://api.ipify.org').content.decode('utf8')

    def addAuth(self, refresh_token=None, exCode=None):
        if refresh_token:
            if refresh_token in {x[1] for x in self.db.getRefreshTokens()}:
                return

            tlHandler = TrueLayerHandler(
                CLIENT_ID,
                CLIENT_SECRET,
                REDIRECT_URI,
                self.ip,
            )
            tlHandler.refresh_token = refresh_token
            res = tlHandler.refreshAccessToken()
            if res.status_code != 200:
                return res.json()
            
            link_id = self.db.addRefreshToken(refresh_token)
        elif exCode:
            tlHandler = TrueLayerHandler(
                CLIENT_ID,
                CLIENT_SECRET,
                REDIRECT_URI,
                self.ip,
            )

            res = tlHandler.authSetup(exCode)
            if res.status_code != 200:
                return res.json()

            refresh_token = res.json()['refresh_token']
            
            link_id = self.db.addRefreshToken(refresh_token)
        else:
            return

        self.tlHandlers[link_id] = tlHandler

        self.addAccounts(link_id)
        self.addCards(link_id)
        self.loadTLHandlers()

    def loadTLHandlers(self):
        for link_id, refresh_token in self.db.getRefreshTokens():
            tlHandler = TrueLayerHandler(
                CLIENT_ID,
                CLIENT_SECRET,
                REDIRECT_URI,
                self.ip, 
                refresh_token=refresh_token
            )

            self.tlHandlers[link_id] = tlHandler
            
            self.loadAccounts(link_id)
            self.loadCards(link_id)

    def loadAccounts(self, link_id):
        self.accounts[link_id] = set()
        for account in self.db.getAccounts(link_id=link_id):
            account_id = account['account_id']

            self.accounts[link_id].add(account_id)
            self.accountToLink[account_id] = link_id
    def loadCards(self, link_id):
        self.cards[link_id] = set()
        for account in self.db.getAccounts(link_id=link_id, cards=True):
            account_id = account['account_id']

            self.cards[link_id].add(account_id)
            self.cardToLink[account_id] = link_id


    def refreshOverdraft(self, account_id, link_id=None, cards=False):
        link_id = link_id if link_id else self.accountToLink[account_id]
        tlHandler = self.tlHandlers[link_id]

        balance = tlHandler.getBalance(account_id, cards).json()['results'][0]
        if cards:
            limit = balance['credit_limit']
            self.db.setCreditLimit(account_id, limit)
        else:
            overdraft = balance['overdraft']
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
            self.refreshOverdraft(account['account_id'], link_id)
    def addCards(self, link_id):
        if self.db.getAccounts(link_id, cards=True):
            return

        tlHander = self.tlHandlers[link_id]

        response = tlHander.getCards()
        if response.status_code != 200:
            return
        
        cards = response.json()['results']
        for card in cards:
            self.db.addCard(link_id=link_id, **card)
            self.refreshOverdraft(card['account_id'], link_id, cards=True)