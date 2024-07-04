from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime

app = Flask(__name__)
app.config.from_object('config.Config')

mongo = PyMongo(app)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({'error': 'Missing data!'}), 400

    try:
        existing_user = mongo.db.users.find_one({'email': email})
        if existing_user:
            return jsonify({'error': 'User already exists!'}), 400

        hashed_password = generate_password_hash(password)
        user_id = mongo.db.users.insert_one({
            'name': name, 
            'email': email, 
            'password': hashed_password
        }).inserted_id

        return jsonify({'message': 'User registered successfully!'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing data!'}), 400

    user = mongo.db.users.find_one({'email': email})
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid credentials!'}), 400

    token = jwt.encode({
        'user_id': str(user['_id']),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'token': token})

@app.route('/protected', methods=['GET'])
def protected():
    token = request.headers.get('Authorization')

    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    try:
        # Extracting token from "Bearer <token>"
        token = token.split()[1]
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired!'}), 401
    except (jwt.InvalidTokenError, IndexError):
        return jsonify({'error': 'Invalid token!'}), 401

    return jsonify({'message': 'This is a protected route.', 'user_id': user_id})


@app.route('/dashboard', methods=['GET'])
def get_devices():
    token = request.headers.get('Authorization')

    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    try:
        token = token.split()[1]
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired!'}), 401
    except (jwt.InvalidTokenError, IndexError, KeyError):
        return jsonify({'error': 'Invalid token!'}), 401

    # Fetch devices from MongoDB
    try:
        devices = list(mongo.db.devices.find())

        # Convert ObjectId to string for JSON serialization
        for device in devices:
            device['_id'] = str(device['_id'])

        return jsonify({'devices': devices})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
