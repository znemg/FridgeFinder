from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"<Ingredient {self.name}>"

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    instructions = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Recipe {self.name}>"
    
class RecipeIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)

    recipe = db.relationship("Recipe", backref="ingredients_needed")