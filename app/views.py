from flask import  jsonify, request

from .database_manager import DatabaseManager
from flask_caching import Cache
from app import app
cache = Cache(app, config={'CACHE_TYPE': 'simple'})  

#  make sure to change the username password with your db username and password
db = DatabaseManager(username='root', password='admin123', db_name='user')
def validate_transaction_payload(data):
    required_fields = ['senderId', 'receiverId', 'amount', 'details']
    for field in required_fields:
        if field not in data:
            return False
    return True
def notify_users(sender_id, receiver_id, transaction_id):
    sender_notification = f"Notification for transaction {transaction_id}: You sent money to {receiver_id}."
    receiver_notification = f"Notification for transaction {transaction_id}: You received money from {sender_id}."
    print(sender_notification)
    print(receiver_notification)
@app.route('/api/transactions/<transactionId>', methods=['GET'])
@cache.cached(timeout=60)
def get_transaction(transactionId):
    if not transactionId:
        return jsonify({"error": "Transaction ID is missing"}), 400
    transaction = db.get_transaction_by_id(transactionId)
    if transaction:
        return jsonify(transaction), 200
    return jsonify({"error": "Transaction not found"}), 404

@app.route('/api/transactions/', methods=['GET'])
@cache.cached(timeout=60)
def get_all_transactions():
    transactions = db.select_all_data('transactions')  
    return jsonify(transactions), 200

@app.route('/api/users/', methods=['GET'])
def get_all_users():
    users = db.select_all_data('users')
    return jsonify(users), 200

@app.route('/api/transactions/', methods=['POST'])
def create_transaction():
    data = request.get_json()
    if not data or not validate_transaction_payload(data):
        return jsonify({"error": "Invalid payload or missing fields"}), 400

    senderId = data.get('senderId')
    receiverId = data.get('receiverId')
    amount = data.get('amount')
    details = data.get('details')

    sender_balance = db.get_user_balance(senderId)
    if sender_balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    result = db.create_transaction( senderId, receiverId, amount, details)
    if result.get('status') == 'Transaction successful':
        notify_users(senderId, receiverId, result.get('transactionId'))

    return jsonify({"message": result}), 201

@app.route('/api/transactions/<transactionId>', methods=['DELETE'])
def reverse_transaction(transactionId):
    if not transactionId:
        return jsonify({"error": "Transaction ID is missing"}), 400
    transaction = db.reverse_transaction(transactionId)
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify({"message": "Transaction reversed"}), 200

if __name__ == '__main__':
    app.run(debug=True)
