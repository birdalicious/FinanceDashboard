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
                `currency` VARCHAR(4),
                `account_number` VARCHAR(8),
                `sort_code` VARCHAR(8),
                PRIMARY KEY (`account_id`),
                FOREIGN KEY (link_id) REFERENCES linked_accounts(id)
            );
            '''
        )

        self.cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS `transactions` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
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

        self.con.commit()

    def insertTransaction(self, **kwargs):
        balance_amount = kwargs['running_balance']['amount']
        balance_currency = kwargs['running_balance']['currency']

        inserts = (
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
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            ''',
            inserts
        )

        self.con.commit()