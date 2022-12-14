from calendar import month
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
            payment_date = balance['payment_due_date']
            self.db.setCreditLimit(account_id, limit)
            self.db.setPaymentDate(account_id, payment_date)
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

    def pullTransactions(self):
        today = date.today()

        # Get latest date transactions were updated
        for link, accounts in self.accounts.items():
            lastestDate = datetime.strptime("3000-01-01",  '%Y-%m-%d').date()

            for account in accounts:
                accountLatestDate = datetime.strptime(self.db.getLastTransaction(account)['timestamp'] , '%Y-%m-%d').date()
                if accountLatestDate < lastestDate:
                    lastestDate = accountLatestDate

            if lastestDate < today:
                self.pullLinkTransactions(link, str(lastestDate), str(today))

    def pullInitialTransactions(self, link_id, days=60):
        today = date.today()
        date_from = today - timedelta(days=days)
        self.pullLinkTransactions(link_id, str(date_from), str(today))

    def pullLinkTransactions(self, link_id, date_from, date_to):
        tlHandler = self.tlHandlers[link_id]

        response = tlHandler.getTransactions(date_from, date_to)
        if response.json()['status'] == 'Failed':
            print(response.json())
            return

        for accountCard in ["accounts", "cards"]:
            for account in response.json()['results'].get(accountCard, []):
                account_id = account['account_id']
                transactions = account['transactions']
                
                lastTransaction = self.db.getLastTransaction(account_id)
                overlap_date_to = date_to if not lastTransaction else lastTransaction['timestamp']
                overlap_date_from = datetime.strptime(date_from, '%Y-%m-%d').date() - timedelta(days=1)

                overlap = {o['normalised_id'] for o in self.db.getTransactions(account_id, overlap_date_from, overlap_date_to)}

                transactions = [r for r in transactions[::-1] if r.get('normalised_provider_transaction_id', r['transaction_id']) not in overlap]
                if len(transactions) == 0:
                    return 

                if account['balance']['current'] == transactions[-1].get("running_balance", {"amount": None})["amount"]:
                    for transaction in transactions:
                        self.db.insertTransaction(account_id=account_id, **transaction)
                    return

                buffer = []
                currentDate = transactions[0]['timestamp']

                # Insert transactions flipping the results of each day for a contiguous ordering
                for transaction in transactions:
                    if transaction['timestamp'] == currentDate:
                        buffer.append(transaction)
                    else:
                        for t in buffer[::-1]:
                            self.db.insertTransaction(account_id=account_id, **t)
                        
                        buffer = [transaction]
                        currentDate = transaction['timestamp']
                for t in buffer[::-1]:
                    self.db.insertTransaction(
                        account_id=account_id,
                        **t
                    )