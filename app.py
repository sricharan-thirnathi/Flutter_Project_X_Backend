from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from dateutil import parser
from dateutil.parser import ParserError
from bson import ObjectId
import re
import google.generativeai as genai


app = Flask(__name__)
app.config.from_object('config.Config')

mongo = PyMongo(app)

genai.configure(api_key=app.config['GENAI_API_KEY'])

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    device_os = data.get('os')

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
            'password': hashed_password,
            'device_os': device_os
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
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24000)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'token': token})

@app.route('/protected', methods=['GET'])
def protected():
    token = request.headers.get('Authorization')

    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    try:
        
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

    
    try:
        devices = list(mongo.db.devices.find())

        
        for device in devices:
            release_date = device.get('releaseDate')
            if release_date:
                try:
                    device['releaseDate'] = parser.parse(release_date)
                except ParserError:
                    device['releaseDate'] = datetime.datetime.min
            else:
                device['releaseDate'] = datetime.datetime.min

        
        devices.sort(key=lambda x: x['releaseDate'], reverse=True)

        
        response_devices = [
            {
                '_id': str(device.get('_id')),
                'model': device.get('model'),
                'image_url': device.get('image_url'),
                'brand': device.get('brand'),
                'releaseDate': device['releaseDate'].strftime('%d %B %Y')
            }
            for device in devices
        ]

        return jsonify({'devices': response_devices})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/product', methods=['POST'])
def get_product():
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

    # Read _id from JSON body
    data = request.get_json()
    product_id = data.get('_id')

    if not product_id:
        return jsonify({'error': 'Product ID is missing!'}), 400

    try:
        if not ObjectId.is_valid(product_id):
            return jsonify({'error': 'Invalid product ID format!'}), 400

        device = mongo.db.devices.find_one({'_id': ObjectId(product_id)})

        if not device:
            return jsonify({'error': 'Product not found!'}), 404

        
        device['_id'] = str(device['_id'])  

        return jsonify({'device': device})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/filter', methods=['POST'])
def filter_devices():
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

   
    filter_data = request.get_json()
    brand = filter_data.get('brand')
    release_year = filter_data.get('releaseDate')  
    market_status = filter_data.get('marketStatus')
    storage = filter_data.get('storage')

    
    print(f"Filter Data: {filter_data}")

    
    query = {}

    if brand:
        
        query['brand'] = re.compile(f'^{re.escape(brand)}$', re.IGNORECASE)

    if release_year:
        try:
            release_year = int(release_year)  
            
            query['releaseDate'] = {
                '$regex': re.compile(r'\b' + re.escape(str(release_year)) + r'\b', re.IGNORECASE)
            }
        except ValueError:
            return jsonify({'error': 'Invalid release year format!'}), 400

    if market_status is not None:
        query['marketStatus'] = market_status

    if storage:
        
        storage_pattern = re.compile(r'\b' + re.escape(storage) + r'\b', re.IGNORECASE)
        
        query['$or'] = [{'fs' + str(i): storage_pattern} for i in range(1, 8)]


    
    try:
        print(f"Query: {query}") 
        devices = list(mongo.db.devices.find(query))

        
        response_devices = [
            {
                '_id': str(device.get('_id')),
                'model': device.get('model'),
                'image_url': device.get('image_url'),
                'brand': device.get('brand'),
                'releaseDate': device.get('releaseDate')
            }
            for device in devices
        ] 

        return jsonify({'devices': response_devices})

    except Exception as e:
        print(f"Exception: {e}")  
        return jsonify({'error': str(e)}), 500
    
@app.route('/search', methods=['POST'])
def search_devices():
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

    
    search_data = request.get_json()
    search_value = search_data.get('search')  

    if not search_value:
        return jsonify({'error': 'No search parameter provided!'}), 400

    
    query = {}

    
    search_conditions = []

    
    search_conditions.append({'brand': re.compile(f'.*{re.escape(search_value)}.*', re.IGNORECASE)})

    
    search_conditions.append({'model': re.compile(f'.*{re.escape(search_value)}.*', re.IGNORECASE)})

    
    try:
        search_year = int(search_value)
        search_conditions.append({'releaseDate': {'$regex': re.compile(r'\b' + re.escape(str(search_year)) + r'\b', re.IGNORECASE)}})
    except ValueError:
        
        pass

    
    try:
        devices = list(mongo.db.devices.find({'$or': search_conditions}))

        
        for device in devices:
            device['_id'] = str(device['_id'])  
        return jsonify({'devices': devices})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


@app.route('/compare', methods=['POST'])
def compare_devices():
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

    
    request_data = request.get_json()
    ids = request_data.get('ids')  

    if not ids or not isinstance(ids, list):
        return jsonify({'error': 'Invalid or missing ids parameter!'}), 400

    
    try:
        object_ids = [ObjectId(id_str) for id_str in ids]
    except Exception as e:
        return jsonify({'error': 'Invalid _id format!'}), 400

    
    try:
        documents = list(mongo.db.devices.find({'_id': {'$in': object_ids}}))
        for doc in documents:
            doc['_id'] = str(doc['_id'])  

        return jsonify({'devices': documents})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/ai', methods=['POST'])
def ai_recommendation():
    
    request_data = request.get_json()
    devices = request_data.get('devices')

    if not devices or len(devices) < 2:
        return jsonify({'error': 'Invalid input! Must provide at least two device documents.'}), 400

    
    prompt = "Compare the following devices and give a recommendation on what product to buy in two lines:\n"
    for device in devices:
        prompt += f"Brand: {device.get('brand')}\n"
        prompt += f"Model: {device.get('model')}\n"
        prompt += f"Display: {device.get('fs1')}\n"
        prompt += f"Processor: {device.get('fs2')}\n"
        prompt += f"Front Camera: {device.get('fs3')}\n"
        prompt += f"Rear Camera: {device.get('fs4')}\n"
        prompt += f"RAM: {device.get('fs5')}\n"
        prompt += f"Storage: {device.get('fs6')}\n"
        prompt += f"OS: {device.get('fs7')}\n"
        prompt += f"Release Date: {device.get('releaseDate')}\n\n"

    
    model = genai.GenerativeModel('gemini-1.5-flash')

    
    try:
        response = model.generate_content(prompt)
        return jsonify({'recommendation': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    
if __name__ == '__main__':
    app.run(debug=True)

