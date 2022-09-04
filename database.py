import sqlite3

class DatabaseHandler:
    def __init__(self, file):
        con = sqlite3.Connection(file)
        cursor = con.cursor()

        cursor.execute(
            ''' 
            CREATE TABLE IF NOT EXISTS linked_accounts (
                id INT AUTO_INCREMENT,
                refresh_token VARCHAR(64),
                PRIMARY_KEY id
            );
            '''
        )

        cursor.execute(
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

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS `transactions` (
                `id` INT AUTO_INCREMENT,
                `account_id` VARCHAR(32) NOT NULL,
                `timestamp` DATE NOT NULL,
                `amount` DECIMAL NOT NULL,
                `merchant_name` VARCHAR(128),
                `description` TEXT,
                `type` VARCHAR(10) NOT NULL,
                `category` VARCHAR(64),
                `classification` TEXT,
                `balance_amount` DECIMAL NOT NULL,
                `balance_currency` VARCHAR(4) NOT NULL,
                PRIMARY KEY (`id`),
                FOREIGN KEY (account_id) REFERENCES accounts(account_id)
            );
            '''
        )

        con.commit()