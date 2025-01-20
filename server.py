from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure CORS for GitHub Pages
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "https://3dimaging.github.io"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Get the environment
ENV = os.getenv('FLASK_ENV', 'production')

# Configure database
if ENV == 'development':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///analytics.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_mobile = db.Column(db.Boolean, nullable=False)
    screen_resolution = db.Column(db.String(20), nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)
    event_data = db.Column(db.JSON)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/api/track-visit', methods=['POST'])
def track_visit():
    try:
        data = request.json
        visit = Visit(
            is_mobile=data.get('isMobile', False),
            screen_resolution=data.get('screenResolution', 'unknown')
        )
        db.session.add(visit)
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/track-event', methods=['POST'])
def track_event():
    try:
        data = request.json
        event = Event(
            event_type=data.get('type'),
            event_data=data.get('data')
        )
        db.session.add(event)
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    try:
        visits = Visit.query.all()
        events = Event.query.all()
        
        analytics_data = {
            'total_visits': len(visits),
            'mobile_visits': sum(1 for v in visits if v.is_mobile),
            'desktop_visits': sum(1 for v in visits if not v.is_mobile),
            'events': [{'type': e.event_type, 'data': e.event_data} for e in events]
        }
        
        return jsonify(analytics_data), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=ENV=='development')
