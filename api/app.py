import os
from upstash_redis import Redis
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

app = Flask(__name__)

CORS(app)
redis = Redis.from_env()


def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'message': 'Blinks API is running!',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'create_blink': 'POST /create-blink',
            'get_redirect': 'GET /b/{blink_url}',
            'list_blinks': 'GET /blinks',
            'blink_info': 'GET /blink/{blink_url}/info',
            'update_blink': 'PUT /blink/{blink_url}',
            'delete_blink': 'DELETE /blink/{blink_url}'
        }
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    try:
        redis.ping()
        return jsonify({'status': 'healthy', 'redis': 'connected'}), 200
    except:
        return jsonify({'status': 'unhealthy', 'redis': 'disconnected'}), 500

@app.route('/create-blink', methods=['POST'])
def create_blink():
    try:
        data = request.get_json()
        
        if not data or 'redirect_url' not in data or 'blink_url' not in data:
            return jsonify({'error': 'Both redirect_url and blink_url are required'}), 400
        
        redirect_url = data['redirect_url']
        blink_url = data['blink_url']

        blink_url = blink_url.lower()
        
        if not redirect_url.startswith(('http://', 'https://')):
            redirect_url = 'http://' + redirect_url

        if not is_valid_url(redirect_url):
            return jsonify({'error': 'Invalid redirect_url format'}), 400
        
        if redis.exists(f"blink:{blink_url}"):
            return jsonify({'error': 'Blink URL already exists'}), 409
        
        blink_data = {
            'redirect_url': redirect_url,
            'created_at': str(int(os.times().system)),
        }
        
        redis.hset(f"blink:{blink_url}", values=blink_data)
        
        return jsonify({
            'blink_url': blink_url,
            'redirect_url': redirect_url,
            'created_at': blink_data['created_at'],
            'message': 'Blink created successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/b/<blink_id>', methods=['GET'])
def redirect_blink(blink_id):
    try:
        blink_data = redis.hgetall(f"blink:{blink_id}")
        
        if not blink_data:
            return jsonify({'error': 'Blink not found'}), 404
                        
        return jsonify({
            'redirect_url': blink_data['redirect_url']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/blink/<blink_id>/info', methods=['GET'])
def get_blink_info(blink_id):
    try:
        blink_data = redis.hgetall(f"blink:{blink_id}")
        
        if not blink_data:
            return jsonify({'error': 'Blink not found'}), 404
        
        return jsonify({
            'blink_url': blink_id,
            'redirect_url': blink_data['redirect_url'],
            'created_at': blink_data['created_at'],
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/blink/<blink_id>', methods=['DELETE'])
def delete_blink(blink_id):
    try:
        if redis.exists(f"blink:{blink_id}"):
            redis.delete(f"blink:{blink_id}")
            return jsonify({'message': 'Blink deleted successfully'}), 200
        else:
            return jsonify({'error': 'Blink not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/blinks', methods=['GET'])
def list_blinks():
    try:
        blink_keys = redis.keys("blink:*")
        blinks = []
        print(blink_keys)
        for key in blink_keys:
            blink_url = key.replace("blink:", "")
            blink_data = redis.hgetall(key)
            
            blinks.append({
                'blink_url': blink_url,
                'redirect_url': blink_data['redirect_url'],
                'created_at': blink_data['created_at'],
            })
        
        return jsonify({
            'blinks': blinks,
            'count': len(blinks)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/blink/<blink_id>', methods=['PUT'])
def update_blink(blink_id):
    try:
        if not redis.exists(f"blink:{blink_id}"):
            return jsonify({'error': 'Blink not found'}), 404
        
        data = request.get_json()
        if not data or 'redirect_url' not in data:
            return jsonify({'error': 'redirect_url is required'}), 400
        
        redirect_url = data['redirect_url']
        
        if not is_valid_url(redirect_url):
            return jsonify({'error': 'Invalid redirect_url format'}), 400
        
        redis.hset(f"blink:{blink_id}", "redirect_url", redirect_url)
        
        blink_data = redis.hgetall(f"blink:{blink_id}")
        
        return jsonify({
            'blink_url': blink_id,
            'redirect_url': blink_data['redirect_url'],
            'created_at': blink_data['created_at'],
            'message': 'Blink updated successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
