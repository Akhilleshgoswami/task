import uuid
import mysql.connector
import json
from decimal import Decimal

class DatabaseManager:
    def __init__(self, username, password, db_name):
        self.username = username
        self.password = password
        self.db_name = db_name
        self.connection = mysql.connector.connect(
            host='localhost',
            user=self.username,
            password=self.password
        )
        self.cursor = self.connection.cursor()
        self.create_database()
        self.use_database()
        self.create_table()
        self.create_transactions_table() 
        self.insert_data_from_json('spec/users.json')
    def create_database(self):
        try:
            self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_name}")
        except mysql.connector.Error as err:
            print(f"Error creating database: {err}")

    def use_database(self):
        try:
            self.cursor.execute(f"USE {self.db_name}")
        except mysql.connector.Error as err:
            print(f"Error selecting database: {err}")

    def create_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    balance VARCHAR(100) NOT NULL
                )
            """)
        except mysql.connector.Error as err:
            print(f"Error creating table: {err}")

    def insert_data_from_json(self, json_path):
        try:
            with open(json_path, 'r') as file:
                users_data = json.load(file)
                for user in users_data:
                    user_id = user.get('id')
                    name = user.get('name')
                    balance = user.get('balance')
                    sql = "INSERT INTO users (id, name, balance) VALUES (%s, %s, %s)"
                    val = (user_id, name, balance)
                    self.cursor.execute(sql, val)
                self.connection.commit()
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading JSON file: {e}")
        except mysql.connector.Error as err:
            print(f"Error inserting data: {err}")
            self.connection.rollback()

    def select_all_data(self, table_name):
        try:
            query = f"SELECT * FROM {table_name}"
            self.cursor.execute(query)
            data = self.cursor.fetchall()
            print(f"All data from the '{table_name}' table:")
            transaction_data = []
            for row in data:
                transaction_data.append(row)
            
            return transaction_data
        except mysql.connector.Error as err:
            print(f"Error retrieving data: {err}")


    def create_transactions_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transactionId VARCHAR(36) PRIMARY KEY,
                    details VARCHAR(255),
                    amount DECIMAL(10, 2),
                    senderId VARCHAR(36),
                    receiverId VARCHAR(36),
                    FOREIGN KEY (senderId) REFERENCES users(id),
                    FOREIGN KEY (receiverId) REFERENCES users(id)
                )
            """)
        except mysql.connector.Error as err:
            print(f"Error creating transactions table: {err}")

    def insert_transaction_data(self, transaction_data):
        try:
            sql = "INSERT INTO transactions (transactionId, details, amount, senderId, receiverId) VALUES (%s, %s, %s, %s, %s)"
            val = (
                transaction_data.get('transactionId'),
                transaction_data.get('details'),
                transaction_data.get('amount'),
                transaction_data.get('senderId'),
                transaction_data.get('receiverId')
            )
            self.cursor.execute(sql, val)
            self.connection.commit()
        except mysql.connector.Error as err:
            print(f"Error inserting transaction data: {err}")
            self.connection.rollback()
    def get_transaction_by_id(self, transactionId):
        try:
            query = "SELECT * FROM transactions WHERE transactionId = %s"
            self.cursor.execute(query, (transactionId,))
            transaction = self.cursor.fetchone()

            if transaction:
                transaction_info = {
                    "transactionId": transaction[0],
                    "details": transaction[1],
                    "amount": float(transaction[2]),
                    "senderId": transaction[3],
                    "receiverId": transaction[4]
                }
                return transaction_info
            else:
                return None
        except mysql.connector.Error as err:
            print(f"Error retrieving transaction: {err}")
            return None

    def create_transaction(self, sender_id, receiver_id, amount, details):
     try:
        transaction_id = str(uuid.uuid4())
        
        # Fetch sender's and receiver's current balances
        sender_balance = self.get_user_balance(sender_id)
        receiver_balance = self.get_user_balance(receiver_id)
        
        if sender_balance >= amount:
            # Deduct amount from sender's balance
            updated_sender_balance = Decimal(sender_balance) - Decimal(amount)
            # Add amount to receiver's balance
            updated_receiver_balance = Decimal(receiver_balance) + Decimal(amount)

            # Update sender's balance in the database
            self.update_user_balance(sender_id, updated_sender_balance)
            # Update receiver's balance in the database
            self.update_user_balance(receiver_id, updated_receiver_balance)
            
            # Insert the transaction record
            sql = "INSERT INTO transactions (transactionId, senderId, receiverId, amount, details) VALUES (%s, %s, %s, %s, %s)"
            val = (transaction_id, sender_id, receiver_id, amount, details)
            self.cursor.execute(sql, val)
            self.connection.commit()
            
            return {"status": "Transaction successful", "transactionId": transaction_id}
        else:
            return {"status": "Insufficient balance"}

     except mysql.connector.Error as err:
        print(f"Error creating transaction: {err}")
        self.connection.rollback()
        return {"status": "Transaction failed"}

    def get_user_balance(self, user_id):
        try:
            # Execute a query to fetch the user's balance from the database
            sql = "SELECT balance FROM users WHERE id = %s"
            val = (user_id,)
            self.cursor.execute(sql, val)
            balance = self.cursor.fetchone()
            
            if balance:
                return balance[0]
            else:
                return None
        except mysql.connector.Error as err:
            print(f"Error fetching user balance: {err}")
            return None

    def reverse_transaction(self, transaction_id):
     try:
        query = "SELECT senderId, receiverId, amount FROM transactions WHERE transactionId = %s"
        self.cursor.execute(query, (transaction_id,))
        transaction_data = self.cursor.fetchone()

        if transaction_data:
            sender_id, receiver_id, amount = transaction_data

            sender_balance = self.get_user_balance(sender_id)
            receiver_balance = self.get_user_balance(receiver_id)

            if sender_balance is not None and receiver_balance is not None:
    
                updated_sender_balance = Decimal(sender_balance)   + Decimal(amount)
                updated_receiver_balance = Decimal(receiver_balance) - Decimal(amount)

                self.update_user_balance(sender_id, updated_sender_balance)
              
                self.update_user_balance(receiver_id, updated_receiver_balance)

       
                print(f"Transaction reversed. Sender's new balance: {updated_sender_balance}, Receiver's new balance: {updated_receiver_balance}")
                delete_query = "DELETE FROM transactions WHERE transactionId = %s"
                self.cursor.execute(delete_query, (transaction_id,))
                self.connection.commit()
                return True
            else:
                print("Unable to fetch balances.")
                return False
        else:
            print("Transaction not found.")
            return False
     except mysql.connector.Error as err:
        print(f"Error reversing transaction: {err}")
        self.connection.rollback()
        return False
    def update_user_balance(self, user_id, new_balance):
        try:
            query = "UPDATE users SET balance = %s WHERE id = %s"
            self.cursor.execute(query, (new_balance, user_id))
            self.connection.commit()
            print(f"User with ID {user_id} balance updated to {new_balance}")
            return True
        except mysql.connector.Error as err:
            print(f"Error updating user balance: {err}")
            self.connection.rollback()
            return False
    
    def close_connection(self):
        self.connection.close()
if __name__ == "__main__":
    db_manager = DatabaseManager('root', 'admin123', 'user')
    db_manager.insert_data_from_json('spec/users.json')
    db_manager.select_all_data('users')
    db_manager.create_transactions_table() 
#     transaction_data ={
#   "transactionId": "2c84bb97-cbd5-4965-9a9d-85e6689d8e89",
#   "details": "Payment to FoodCompany Inc. ",
#   "amount": 1500,
#   "senderId": "f1729ae4-67b9-46f8-bd15-5802bc29ae96",
#   "receiverId": "a845c744-d677-41a0-b29b-30fd18e8c117"
# }

#     db_manager.insert_transaction_data(transaction_data)  # Insert transaction data
#     db_manager.select_all_data('transactions')  
#     db_manager.close_connection()
