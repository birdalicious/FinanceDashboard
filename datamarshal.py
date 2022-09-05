import os
import requests

from database import DatabaseHandler
from truelayer import TrueLayerHandler

from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("TRUELAYER_CLIENT_ID")
CLIENT_SECRET = os.getenv("TRUELAYER_CLIENT_SECRET")
REDIRECT_URI = os.getenv("TRUELAYER_REDIRECT_URI")

class DataMarshaller:
    def __init__(self, databaseFile, ip=None):
        self.ip = ip if ip else self.getIP()
        self.db = DatabaseHandler(databaseFile)

        self.accounts = {}
        

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

            for account in self.db.getAccounts(link_id=link_id):
                self.accounts[account['account_id']] = tlHandler


    def addAuthToken(self, refreshToken=None, exCode=None):
        if refreshToken:
            if refreshToken in {x[1] for x in self.db.getRefreshTokens()}:
                return

            tlHandler = TrueLayerHandler(
                CLIENT_ID,
                CLIENT_SECRET,
                REDIRECT_URI,
                self.ip,
            )
            tlHandler.refresh_token = refreshToken
            res = tlHandler.refreshAccessToken()
            if res.status_code != 200:
                return res.json()
            
            link_id = self.db.addRefreshToken(refreshToken)
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
            
            link_id = self.db.addRefreshToken(refreshToken)
        else:
            return

        accounts = tlHandler.makeRequest(tlHandler.requestAccounts).json()['results']
        for account in accounts:
            overdraft = tlHandler.makeRequest(tlHandler.requestBalance, account['account_id']).json()['results'][0]['overdraft']
            self.db.addAccount(link_id=link_id, overdraft=overdraft, **account)

        return [(link_id, account['account_id']) for account in accounts]