import os

from flask import Flask, render_template, request, redirect, flash # type: ignore
from flask_login import LoginManager, login_user, logout_user, login_required, current_user # type: ignore
from flask_bcrypt import Bcrypt #type: ignore
from models import db, Ingredient, Recipe, RecipeIngredient, User
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = 'super-secret-fridge-key-123'

# Configure SQLite database
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'fridge.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with app
db.init_app(app)

# Initialize the bcrypt password hashing func
bcrypt = Bcrypt(app)

# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect('/')
        flash('Invalid credentials.', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register.html')
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'error')
            return render_template('register.html')
        
        # Check password length
        if len(password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return render_template('register.html')
        
        # Hash password and create user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect('/login')
    return render_template('register.html')

# Unit conversion
unit_conversion = {
    # Weight to g
    'g': 1, 
    'kg': 1000, 
    'oz': 28.3495, 
    'lb': 453.592,
    'mg': 0.001,
    't': 1000000,  # metric ton
    
    # Volume to ml
    'ml': 1, 
    'l': 1000, 
    'tsp': 4.92892, 
    'tbsp': 14.7868, 
    'cup': 240, 
    'fl oz': 29.5735,
    'pint': 473.176,
    'quart': 946.353,
    'gallon': 3785.41,
    'cc': 1,  # cubic centimeter = ml
    
    # Count units
    'pcs': 1, 
    'each': 1, 
    'dozen': 12,
    'piece': 1,
    'whole': 1,
    'slice': 1,
    'clove': 1,  # for garlic
    'bunch': 1,
    'head': 1,  # for lettuce, cabbage
}

def convert_unit(amount, from_unit, to_unit):
    """
    Convert amount from one unit to another.
    Returns None if conversion is not possible.
    """
    if from_unit == to_unit:
        return amount
    
    # Normalize units (handle common variations)
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()
    
    # Handle common unit variations
    unit_aliases = {
        'gram': 'g', 'grams': 'g',
        'kilogram': 'kg', 'kilograms': 'kg',
        'ounce': 'oz', 'ounces': 'oz',
        'pound': 'lb', 'pounds': 'lb',
        'milliliter': 'ml', 'milliliters': 'ml',
        'liter': 'l', 'liters': 'l',
        'teaspoon': 'tsp', 'teaspoons': 'tsp',
        'tablespoon': 'tbsp', 'tablespoons': 'tbsp',
        'fluid ounce': 'fl oz', 'fluid ounces': 'fl oz',
        'piece': 'pcs', 'pieces': 'pcs',
        'whole': 'pcs',
        'clove': 'pcs', 'cloves': 'pcs',
        'bunch': 'pcs', 'bunches': 'pcs',
        'head': 'pcs', 'heads': 'pcs',
    }
    
    from_unit = unit_aliases.get(from_unit, from_unit)
    to_unit = unit_aliases.get(to_unit, to_unit)
    
    # Ensure we have valid strings
    if not from_unit or not to_unit:
        return None
    
    try:
        return amount * (unit_conversion[from_unit] / unit_conversion[to_unit])
    except KeyError:
        return None  # Unknown unit


# Home route
@app.route('/')
@login_required
def index():
    ingredients = Ingredient.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', ingredients = current_user.ingredients)  # shows the homepage

@app.route('/add', methods = ['GET', 'POST'])
@login_required
def add_ingredients():
    if request.method == 'POST':
        name = request.form['name']
        quantity = float(request.form['quantity'])
        unit = request.form['unit']
        expiry_date_str = request.form['expiry_date']
        expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date() if expiry_date_str else None

        # First, try to find an existing ingredient with the same name and unit
        existed = Ingredient.query.filter_by(name=name, unit=unit).first()
        
        if existed:
            # Same name and unit - just add quantities
            existed.quantity += quantity
            if expiry_date:
                existed.expiry_date = expiry_date
        else:
            # Check if there's an existing ingredient with the same name but different unit
            existing_same_name = Ingredient.query.filter_by(name=name).first()
            
            if existing_same_name:
                # Convert the new quantity to the existing unit
                converted_quantity = convert_unit(quantity, unit, existing_same_name.unit)
                
                if converted_quantity is not None:
                    # Units are compatible - combine them
                    existing_same_name.quantity += converted_quantity
                    if expiry_date:
                        existing_same_name.expiry_date = expiry_date
                    flash(f'Added {quantity} {unit} of {name} (converted to {converted_quantity:.2f} {existing_same_name.unit})', 'success')
                else:
                    # Units are incompatible - create new entry
                    ingredient = Ingredient(
                        name=name,
                        quantity=quantity,
                        unit=unit,
                        expiry_date=expiry_date,
                        user_id=current_user.id
                    )
                    db.session.add(ingredient)
                    flash(f'Added {quantity} {unit} of {name} (incompatible units with existing {existing_same_name.unit})', 'warning')
            else:
                # No existing ingredient with this name - create new entry
                ingredient = Ingredient(
                    name=name,
                    quantity=quantity,
                    unit=unit,
                    expiry_date=expiry_date,
                    user_id=current_user.id
                )
                db.session.add(ingredient)
        
        db.session.commit()
        return redirect('/')
    return render_template('add_ingredients.html')

@app.route('/recipes')
@login_required
def recipe_recommendations():
    recipes = Recipe.query.filter_by(user_id=current_user.id).all()
    fridge = Ingredient.query.filter_by(user_id=current_user.id).all()
    fridge_dict = {item.name.lower(): item for item in fridge}

    entries = []

    for recipe in recipes:
        missing = []
        can_make = True
        
        for req in recipe.ingredients_needed:
            in_fridge = fridge_dict.get(req.name.lower())
            
            if not in_fridge:
                missing.append({
                    'name': req.name,
                    'needed': req.quantity,
                    'unit': req.unit,
                    'available': 0
                })
                can_make = False
            else:
                # Try to convert units for comparison
                converted_available = convert_unit(in_fridge.quantity, in_fridge.unit, req.unit)
                
                if converted_available is None:
                    # Units are incompatible, treat as missing
                    missing.append({
                        'name': req.name,
                        'needed': req.quantity,
                        'unit': req.unit,
                        'available': f"{in_fridge.quantity} {in_fridge.unit} (incompatible units)"
                    })
                    can_make = False
                elif converted_available < req.quantity:
                    missing.append({
                        'name': req.name,
                        'needed': req.quantity,
                        'unit': req.unit,
                        'available': round(converted_available, 2)
                    })
                    can_make = False
        
        entries.append({
            'recipe': recipe,
            'can_make': can_make,
            'almost_can_make': len(missing) <= 2,
            'missing_ingredients': missing
        })
            
    return render_template('recipes.html', entries=entries)

@app.route('/add_recipe', methods = ['GET', 'POST'])
@login_required
def add_recipe():
    if request.method == 'POST':
        name = request.form['name']
        instructions = request.form['instructions']
        recipe = Recipe(name=name, instructions=instructions, user_id=current_user.id)
        db.session.add(recipe)
        db.session.commit()
    
        for i in range(5):
            ing_name = request.form.get(f'ingredient_name_{i}')
            ing_qty = request.form.get(f'ingredient_quantity_{i}')
            ing_unit = request.form.get(f'ingredient_unit_{i}')

            if ing_name and ing_qty and ing_unit:
                ingredient = RecipeIngredient(
                    recipe_id = recipe.id,
                    name = ing_name.strip().lower(),
                    quantity = float(ing_qty),
                    unit = ing_unit.strip()
                )
                db.session.add(ingredient)
        
        db.session.commit()
        return redirect('/recipes')
    
    return render_template('add_recipe.html')

@app.route('/make_recipe/<int:recipe_id>', methods=['POST'])
@login_required
def make_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    fridge = Ingredient.query.filter_by(user_id=current_user.id).all()
    fridge_dict = {item.name.lower(): item for item in fridge}

    # Check if we have enough ingredients with unit conversion
    for req in recipe.ingredients_needed:
        in_fridge = fridge_dict.get(req.name.lower())
        if not in_fridge:
            flash('Not enough ingredients to make this recipe.', 'error')
            return redirect('/recipes')
        
        # Try to convert units for comparison
        converted_available = convert_unit(in_fridge.quantity, in_fridge.unit, req.unit)
        
        if converted_available is None:
            flash(f'Incompatible units for {req.name}.', 'error')
            return redirect('/recipes')
        
        if converted_available < req.quantity:
            flash('Not enough ingredients to make this recipe.', 'error')
            return redirect('/recipes')
    
    # Deduct ingredients with unit conversion
    for req in recipe.ingredients_needed:
        ingredient = fridge_dict[req.name.lower()]
        
        # Convert the required amount to the ingredient's unit
        converted_needed = convert_unit(req.quantity, req.unit, ingredient.unit)
        
        if converted_needed is None:
            flash(f'Error converting units for {req.name}.', 'error')
            return redirect('/recipes')
        
        ingredient.quantity -= converted_needed
        if ingredient.quantity <= 0:
            db.session.delete(ingredient)
    
    db.session.commit()
    flash(f'{recipe.name} made! Ingredients deducted from fridge.', 'success')
    return redirect('/recipes')

@app.route('/all_recipes')
def all_recipes():
    recipes = Recipe.query.filter_by(user_id=current_user.id).all()
    return render_template('all_recipes.html', recipes=recipes)

@app.route('/update_quantity/<int:id>', methods=['POST'])
@login_required
def update_quantity(id):
    ingredient = Ingredient.query.get_or_404(id)
    new_quantity = request.form.get('quantity')
    try:
        ingredient.quantity = float(new_quantity)
        db.session.commit()
        flash(f'Updated {ingredient.name} quantity to {new_quantity}', 'success')
    except:
        flash('Invalid quantity input.', 'error')
    return redirect('/')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect('/login')

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
