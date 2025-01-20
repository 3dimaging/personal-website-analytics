from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure CORS for GitHub Pages
CORS(app)

# Get the environment
ENV = os.getenv('FLASK_ENV', 'production')

# Configure database
if ENV == 'development':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///analytics.db'
else:
    # Get DATABASE_URL from environment variable
    database_url = os.getenv('DATABASE_URL')
    # Modify the URL for SQLAlchemy if it starts with postgres://
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

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

@app.route('/', methods=['GET'])
def home():
    return jsonify({'status': 'ok', 'message': 'Analytics API is running'}), 200

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
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        db.session.close()

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
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        db.session.close()

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
    finally:
        db.session.close()

@app.route('/dashboard')
def dashboard():
    try:
        visits = Visit.query.order_by(Visit.timestamp).all()
        
        # Calculate basic stats
        total_visits = len(visits)
        mobile_visits = sum(1 for v in visits if v.is_mobile)
        desktop_visits = total_visits - mobile_visits

        # Prepare visit data for the time series chart
        from collections import defaultdict
        
        visit_dates = defaultdict(int)
        for visit in visits:
            date_str = visit.timestamp.strftime('%Y-%m-%d')
            visit_dates[date_str] += 1
        
        # Sort dates and prepare data for the chart
        sorted_dates = sorted(visit_dates.keys())
        visit_counts = [visit_dates[date] for date in sorted_dates]

        return render_template_string(DASHBOARD_HTML,
            total_visits=total_visits,
            mobile_visits=mobile_visits,
            desktop_visits=desktop_visits,
            visit_dates=sorted_dates,
            visit_counts=visit_counts
        )
    except Exception as e:
        return str(e), 500
    finally:
        db.session.close()

# HTML template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
        }
        .stat-number {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-label {
            color: #7f8c8d;
            margin-top: 5px;
        }
        .chart-container {
            margin-top: 30px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Website Analytics Dashboard</h1>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_visits }}</div>
                <div class="stat-label">Total Visits</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ mobile_visits }}</div>
                <div class="stat-label">Mobile Visits</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ desktop_visits }}</div>
                <div class="stat-label">Desktop Visits</div>
            </div>
        </div>

        <div class="chart-container">
            <canvas id="deviceChart"></canvas>
        </div>

        <div class="chart-container">
            <canvas id="visitsChart"></canvas>
        </div>
    </div>

    <script>
        // Device distribution chart
        const deviceCtx = document.getElementById('deviceChart').getContext('2d');
        new Chart(deviceCtx, {
            type: 'pie',
            data: {
                labels: ['Mobile', 'Desktop'],
                datasets: [{
                    data: [{{ mobile_visits }}, {{ desktop_visits }}],
                    backgroundColor: ['#3498db', '#2ecc71']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Device Distribution'
                    }
                }
            }
        });

        // Visits over time chart
        const visitsCtx = document.getElementById('visitsChart').getContext('2d');
        new Chart(visitsCtx, {
            type: 'line',
            data: {
                labels: {{ visit_dates | safe }},
                datasets: [{
                    label: 'Visits',
                    data: {{ visit_counts | safe }},
                    borderColor: '#3498db',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Visits Over Time'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""

# Vercel requires a handler function
app.debug = ENV == 'development'

def handler(event, context):
    return app
