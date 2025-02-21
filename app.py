from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///nutrition.db')
# Fix for Postgres URL on Vercel
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# USDA API configuration
USDA_API_KEY = os.getenv('USDA_API_KEY', 'DEMO_KEY')
USDA_API_BASE_URL = 'https://api.nal.usda.gov/fdc/v1'

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    food_logs = db.relationship('FoodLog', backref='user', lazy=True)
    daily_goals = db.relationship('NutritionGoal', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_name = db.Column(db.String(100), nullable=False)
    serving_size = db.Column(db.Float, nullable=False)
    calories = db.Column(db.Float, nullable=False)
    protein = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)  # breakfast, lunch, dinner, snack
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    usda_food_id = db.Column(db.String(20), nullable=True)

class NutritionGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    calories = db.Column(db.Float, nullable=False, default=2000)
    protein = db.Column(db.Float, nullable=False, default=50)
    carbs = db.Column(db.Float, nullable=False, default=250)
    fat = db.Column(db.Float, nullable=False, default=70)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Local food database for fallback
LOCAL_FOOD_DB = {
    'apple': {'calories': 95, 'protein': 0.5, 'carbs': 25, 'fat': 0.3},
    'banana': {'calories': 105, 'protein': 1.3, 'carbs': 27, 'fat': 0.4},
    'chicken breast': {'calories': 165, 'protein': 31, 'carbs': 0, 'fat': 3.6},
    'rice': {'calories': 130, 'protein': 2.7, 'carbs': 28, 'fat': 0.3},
    'egg': {'calories': 70, 'protein': 6, 'carbs': 0, 'fat': 5},
    'milk': {'calories': 103, 'protein': 8, 'carbs': 12, 'fat': 2.4},
}

# USDA API Functions with fallback
def search_food_usda(query):
    # First try USDA API
    try:
        response = requests.get(
            f'{USDA_API_BASE_URL}/foods/search',
            params={
                'api_key': USDA_API_KEY,
                'query': query,
                'dataType': ['Survey (FNDDS)'],
                'pageSize': 10
            },
            timeout=5  # Add timeout to avoid hanging
        )
        response.raise_for_status()
        data = response.json()
        
        results = [{
            'food_id': food['fdcId'],
            'name': food['description'],
            'source': 'usda',
            'nutrients': {
                'calories': next((n['value'] for n in food.get('foodNutrients', []) if n['nutrientName'] == 'Energy'), 0),
                'protein': next((n['value'] for n in food.get('foodNutrients', []) if n['nutrientName'] == 'Protein'), 0),
                'carbs': next((n['value'] for n in food.get('foodNutrients', []) if n['nutrientName'] == 'Carbohydrate, by difference'), 0),
                'fat': next((n['value'] for n in food.get('foodNutrients', []) if n['nutrientName'] == 'Total lipid (fat)'), 0)
            }
        } for food in data.get('foods', [])]
        
        if results:  # If we got results from USDA, return them
            return results
            
    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        print(f'USDA API Error: {e}')
    
    # Fallback to local database if USDA API fails or returns no results
    local_results = []
    query = query.lower()
    for food_name, nutrients in LOCAL_FOOD_DB.items():
        if query in food_name:
            local_results.append({
                'food_id': f'local_{food_name.replace(" ", "_")}',
                'name': food_name.title(),
                'source': 'local',
                'nutrients': nutrients
            })
    
    return local_results

# Auth routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('home'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Main routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/api/search-food')
@login_required
def search_food():
    query = request.args.get('query', '')
    if not query:
        return jsonify({'results': []})
    
    results = search_food_usda(query)
    return jsonify({'results': results})

@app.route('/api/log-food', methods=['POST'])
@login_required
def log_food():
    try:
        data = request.json
        if not all(k in data for k in ['food_name', 'serving_size', 'calories']):
            return jsonify({
                'status': 'error',
                'message': 'Missing required food data'
            }), 400

        # Set default values if nutritional info is missing
        new_log = FoodLog(
            user_id=current_user.id,
            food_name=data['food_name'],
            serving_size=float(data['serving_size']),
            calories=float(data['calories']),
            protein=float(data.get('protein', 0)),
            carbs=float(data.get('carbs', 0)),
            fat=float(data.get('fat', 0)),
            meal_type=data.get('meal_type', 'snack'),
            usda_food_id=data.get('usda_food_id')
        )
        
        db.session.add(new_log)
        db.session.commit()
        return jsonify({'status': 'success'})
        
    except (ValueError, KeyError, TypeError) as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred'
        }), 500

@app.route('/api/get-logs')
@login_required
def get_logs():
    try:
        # Get date from query parameters, default to today
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400

        # Query logs with error handling
        try:
            logs = FoodLog.query.filter(
                FoodLog.user_id == current_user.id,
                db.func.date(FoodLog.date) == date.date()
            ).all()
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': 'Database error occurred'
            }), 500

        # Format the response
        log_data = [{
            'id': log.id,
            'food_name': log.food_name,
            'serving_size': log.serving_size,
            'calories': log.calories,
            'protein': log.protein,
            'carbs': log.carbs,
            'fat': log.fat,
            'meal_type': log.meal_type,
            'date': log.date.strftime('%Y-%m-%d %H:%M:%S')
        } for log in logs]

        return jsonify({
            'status': 'success',
            'data': log_data
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred'
        }), 500

@app.route('/api/nutrition-goals', methods=['GET', 'POST'])
@login_required
def nutrition_goals():
    if request.method == 'POST':
        data = request.json
        goal = NutritionGoal.query.filter_by(user_id=current_user.id).first()
        if not goal:
            goal = NutritionGoal(user_id=current_user.id)
            db.session.add(goal)
        
        goal.calories = data.get('calories', 2000)
        goal.protein = data.get('protein', 50)
        goal.carbs = data.get('carbs', 250)
        goal.fat = data.get('fat', 70)
        
        db.session.commit()
        return jsonify({'status': 'success'})
    
    goal = NutritionGoal.query.filter_by(user_id=current_user.id).first()
    if not goal:
        return jsonify({
            'calories': 2000,
            'protein': 50,
            'carbs': 250,
            'fat': 70
        })
    
    return jsonify({
        'calories': goal.calories,
        'protein': goal.protein,
        'carbs': goal.carbs,
        'fat': goal.fat
    })

with app.app_context():
    db.create_all()

# For Vercel deployment
app.debug = False

if __name__ == '__main__':
    app.run()
