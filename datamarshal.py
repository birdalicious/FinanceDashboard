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
    def __init__(self, databaseFile, ip=None):
        self.ip = ip if ip else self.getIP()
        self.db = DatabaseHandler(databaseFile)

        self.accounts = {}

        self.loadAccounts()

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

            refreshToken = res.json()['refresh_token']
            
            link_id = self.db.addRefreshToken(refreshToken)
        else:
            return

        response = tlHandler.makeRequest(tlHandler.requestAccounts)
        accounts = response.json()['results']

        for account in accounts:
            balance = tlHandler.makeRequest(tlHandler.requestBalance, account['account_id']).json()['results'][0]

            overdraft = balance['overdraft']

            self.db.addAccount(link_id=link_id, overdraft=overdraft, **account)

        return [(link_id, account['account_id']) for account in accounts]


    def pullInitialTransactions(self, account_id, date_from=None, date_to=None):
        if self.db.getLastTransaction(account_id):
            return
        tlHandler = self.accounts[account_id]
        response = tlHandler.makeRequest(
            tlHandler.requestTransactions,
            account_id,
            date_from=date_from,
            date_to=date_to
        )

        results = response.json()['results']
        print(results)
        for result in results[::-1]:
            self.db.insertTransaction(account_id=account_id, **result)

    def mergeTransactions(self, account_id, fetched_transactions, date_from, date_to):
        last = self.db.getLastTransaction(account_id)

        #Check the overlap
        dbOverlap = {o[1] for o in self.db.getTransactions(account_id, date_from=date_from, date_to=last['timestamp'])}

        return [r for r in fetched_transactions[::-1] if r['normalised_provider_transaction_id'] not in dbOverlap]
    
    def pullAccountTransactions(self, account_id):
        last = self.db.getLastTransaction(account_id)
        if not last:
            return self.pullInitialTransactions(account_id)
        date_from = datetime.strptime(last['timestamp'], '%Y-%m-%d').date() - timedelta(days=1)
        date_to = date.today()
        
        tlHandler = self.accounts[account_id]
        response = tlHandler.makeRequest(
            tlHandler.requestTransactions,
            account_id,
            date_from=date_from,
            date_to=date_to
        )
        results = response.json()['results']

        for result in self.mergeTransactions(account_id, results, date_from, date_to):
            self.db.insertTransaction(account_id=account_id, **result)

    def pullTransactions(self):
        for account_id, _ in self.accounts.items():
            self.pullAccountTransactions(account_id)