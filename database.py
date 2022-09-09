import sqlite3

class DatabaseHandler:
    def __init__(self, file):
        self.con = sqlite3.Connection(file)
        self.cursor = self.con.cursor()

        self.cursor.execute(
            ''' 
            CREATE TABLE IF NOT EXISTS linked_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                refresh_token VARCHAR(64)
            );
            '''
        )

        self.cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS `accounts` (
                `account_id` VARCHAR(32) NOT NULL,
                `link_id` INT,
                `type` VARCHAR(64),
                `display_name` TEXT,
                `overdraft` DECIMAL,
                `currency` VARCHAR(4),
                `account_number` VARCHAR(8),
                `sort_code` VARCHAR(8),
                `expired` BOOLEAN NOT NULL,
                PRIMARY KEY (`account_id`),
                FOREIGN KEY (link_id) REFERENCES linked_accounts(id)
            );
            '''
        )

        self.cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS `cards` (
                `account_id` VARCHAR(32) NOT NULL,
                `link_id` INT,
                `type` VARCHAR(64),
                `display_name` TEXT,
                `credit_limit` DECIMAL,
                `currency` VARCHAR(4),
                `card_number` VARCHAR(8),
                `expired` BOOLEAN NOT NULL,
                PRIMARY KEY (`account_id`),
                FOREIGN KEY (link_id) REFERENCES linked_accounts(id)
            );
            '''
        )

        self.cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS `transactions` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `normalised_id` VARCHAR(128),
                `account_id` VARCHAR(32) NOT NULL,
                `timestamp` DATE NOT NULL,
                `amount` DECIMAL NOT NULL,
                `currency` VARCHAR(4) NOT NULL,
                `merchant_name` VARCHAR(128),
                `description` TEXT,
                `type` VARCHAR(10) NOT NULL,
                `category` VARCHAR(64),
                `classification` TEXT,
                `balance_amount` DECIMAL NOT NULL,
                `balance_currency` VARCHAR(4) NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(account_id)
            );
            '''
        )

        self.cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS `pending_transactions` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `normalised_id` VARCHAR(128),
                `account_id` VARCHAR(32) NOT NULL,
                `timestamp` DATE NOT NULL,
                `amount` DECIMAL NOT NULL,
                `currency` VARCHAR(4) NOT NULL,
                `merchant_name` VARCHAR(128),
                `description` TEXT,
                `type` VARCHAR(10) NOT NULL,
                `category` VARCHAR(64),
                `classification` TEXT,
                FOREIGN KEY (account_id) REFERENCES accounts(account_id)
            );
            '''
        )

        self.con.commit()

    def addRefreshToken(self, refresh_token):
        self.cursor.execute(
            '''
            INSERT INTO linked_accounts (
                refresh_token
            )
            VALUES (
                ?
            )
            ''',
            (refresh_token,)
        )

        self.con.commit()

        return self.cursor.lastrowid

    def getRefreshTokens(self, link_id=None):
        if link_id:
            res = self.cursor.execute(
                '''
                SELECT * FROM linked_accounts
                WHERE id = ?
                ''',
                (link_id,)
            )
        else:
            res = self.cursor.execute(
                "SELECT * FROM linked_accounts"
            )
        
        results = res.fetchall()
        return results

    def addCard(self, **kwargs):
        link_id = kwargs.get('link_id', None)
        if not link_id:
            res = self.cursor.execute(
                '''
                SELECT id
                FROM linked_accounts
                WHERE refresh_token = ?
                ''',
                (kwargs['refresh_token'],)
            )
            link_id = res.fetchone()[0]

        inserts = (
            kwargs['account_id'],
            link_id,
            kwargs['card_type'],
            kwargs['display_name'],
            kwargs.get('credit_limit', 0),
            kwargs['currency'],
            kwargs['partial_card_number'],
        )

        self.cursor.execute(
            '''
            INSERT INTO cards (
                account_id,
                link_id,
                type,
                display_name,
                credit_limit,
                currency,
                card_number,
                expired
            )
            VALUES (
                ?,?,?,?,?,?,?, 0
            )
            ''',
            inserts
        )

        self.con.commit()

        return self.cursor.lastrowid

    def addAccount(self, **kwargs):
        link_id = kwargs.get('link_id', None)
        if not link_id:
            res = self.cursor.execute(
                '''
                SELECT id
                FROM linked_accounts
                WHERE refresh_token = ?
                ''',
                (kwargs['refresh_token'],)
            )
            link_id = res.fetchone()[0]

        inserts = (
            kwargs['account_id'],
            link_id,
            kwargs['account_type'],
            kwargs['display_name'],
            kwargs.get('overdraft', 0),
            kwargs['currency'],
            kwargs['account_number']['number'],
            kwargs['account_number']['sort_code'],
        )

        self.cursor.execute(
            '''
            INSERT INTO accounts (
                account_id,
                link_id,
                type,
                display_name,
                overdraft,
                currency,
                account_number,
                sort_code,
                expired
            )
            VALUES (
                ?,?,?,?,?,?,?,?, 0
            )
            ''',
            inserts
        )

        self.con.commit()

        return self.cursor.lastrowid
    
    def setOverdraft(self, account_id, overdraft):
        self.cursor.execute(
            '''
                UPDATE accounts
                SET overdraft = ?
                WHERE account_id = ?
            ''',
            (overdraft, account_id)
        )

        self.con.commit()

    def setCreditLimit(self, account_id, limit):
        self.cursor.execute(
            '''
                UPDATE cards
                SET credit_limit = ?
                WHERE account_id = ?
            ''',
            (limit, account_id)
        )

        self.con.commit()

    def getAccounts(self, link_id=None, cards=False):
        table = 'cards' if cards else 'accounts'
        if link_id:
            res = self.cursor.execute(
                f'''
                SELECT * FROM {table}
                WHERE link_id = ?
                ''',
                (link_id, )
            )
        else:
            res = self.cursor.execute(
                f"SELECT * FROM {table}"
            )

        results = res.fetchall()
        keys = [x[0] for x in self.cursor.description]

        return [{k: v for k,v in zip(keys, result)} for result in results] if results else []


    def insertTransaction(self, **kwargs):
        balance_amount = kwargs['running_balance']['amount']
        balance_currency = kwargs['running_balance']['currency']

        inserts = (
            kwargs['normalised_provider_transaction_id'],
            kwargs['account_id'],
            kwargs['timestamp'][:10],
            kwargs['amount'],
            kwargs['currency'],
            kwargs.get('merchant_name', None),
            kwargs['description'],
            kwargs['transaction_type'],
            kwargs['transaction_category'],
            str(kwargs['transaction_classification']),
            balance_amount,
            balance_currency
            )

        self.cursor.execute(
            '''
            INSERT INTO transactions (
                normalised_id,
                account_id,
                timestamp,
                amount,
                currency,
                merchant_name,
                description,
                type,
                category,
                classification,
                balance_amount,
                balance_currency
            )
            VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?
            )
            ''',
            inserts
        )

        self.con.commit()
    
    def getTransactions(self, account_id, date_from=None, date_to=None):
        if date_from and date_to:
            res = self.cursor.execute(
                '''
                SELECT * FROM transactions
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp;
                ''',
                (date_from, date_to)
            )
        else:
            res = self.cursor.execute(
                '''
                SELECT * FROM transactions
                ORDER BY timestamp;
                '''
            )

        return res.fetchall()

    def insertPendingTransaction(self, **kwargs):
        inserts = (
            kwargs['normalised_provider_transaction_id'],
            kwargs['account_id'],
            kwargs['timestamp'][:10],
            kwargs['amount'],
            kwargs['currency'],
            kwargs.get('merchant_name', None),
            kwargs['description'],
            kwargs['transaction_type'],
            kwargs['transaction_category'],
            str(kwargs['transaction_classification']),
            )

        self.cursor.execute(
            '''
            INSERT INTO transactions (
                normalised_id,
                account_id,
                timestamp,
                amount,
                currency,
                merchant_name,
                description,
                type,
                category,
                classification,
                balance_amount,
                balance_currency
            )
            VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?
            )
            ''',
            inserts
        )

        self.con.commit()

    def getLastTransaction(self, account_id):
        res = self.cursor.execute(
            '''
            SELECT 
            *
            FROM 
            transactions 
            WHERE account_id=?
            ORDER BY timestamp DESC LIMIT 1
            ''',
            (account_id,)
        )

        out = res.fetchone()
        return {k[0]:v for k, v in zip(self.cursor.description, out)} if out else None

    def getBalance(self, account_id):
        last = self.getLastTransaction(account_id)
        if last:
            return (last['balance_amount'], last['balance_currency'])
        return None