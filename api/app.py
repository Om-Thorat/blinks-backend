import os
import redis
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

app = Flask(__name__)

CORS(app)
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
redis_client = redis.from_url(redis_url, decode_responses=True)


def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

@app.route('/health', methods=['GET'])
def health_check():
    try:
        redis_client.ping()
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
        
        if not is_valid_url(redirect_url):
            return jsonify({'error': 'Invalid redirect_url format'}), 400
        
        if redis_client.exists(f"blink:{blink_url}"):
            return jsonify({'error': 'Blink URL already exists'}), 409
        
        blink_data = {
            'redirect_url': redirect_url,
            'created_at': str(int(os.times().system)),
        }
        
        redis_client.hset(f"blink:{blink_url}", mapping=blink_data)
        
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
        blink_data = redis_client.hgetall(f"blink:{blink_id}")
        
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
        blink_data = redis_client.hgetall(f"blink:{blink_id}")
        
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
        if redis_client.exists(f"blink:{blink_id}"):
            redis_client.delete(f"blink:{blink_id}")
            return jsonify({'message': 'Blink deleted successfully'}), 200
        else:
            return jsonify({'error': 'Blink not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/blinks', methods=['GET'])
def list_blinks():
    try:
        blink_keys = redis_client.keys("blink:*")
        blinks = []
        
        for key in blink_keys:
            blink_url = key.replace("blink:", "")
            blink_data = redis_client.hgetall(key)
            
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
        if not redis_client.exists(f"blink:{blink_id}"):
            return jsonify({'error': 'Blink not found'}), 404
        
        data = request.get_json()
        if not data or 'redirect_url' not in data:
            return jsonify({'error': 'redirect_url is required'}), 400
        
        redirect_url = data['redirect_url']
        
        if not is_valid_url(redirect_url):
            return jsonify({'error': 'Invalid redirect_url format'}), 400
        
        redis_client.hset(f"blink:{blink_id}", "redirect_url", redirect_url)
        
        blink_data = redis_client.hgetall(f"blink:{blink_id}")
        
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
