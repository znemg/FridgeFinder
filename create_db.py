import os
print("Creating database in:", os.path.abspath("fridge.db"))

from app import app
from models import db

from models import Recipe, RecipeIngredient

with app.app_context():
    db.create_all()
    print("✅ Database and tables created!")
    # Add a recipe: Avocado Salad
    salad = Recipe(name="Avocado Salad", instructions="Mix avocado, kale, arugula, and olive oil.")
    db.session.add(salad)
    db.session.commit()

    # Add required ingredients for it
    items = [
        RecipeIngredient(recipe_id=salad.id, name="avocado", quantity=1, unit="pcs"),
        RecipeIngredient(recipe_id=salad.id, name="kale", quantity=50, unit="g"),
        RecipeIngredient(recipe_id=salad.id, name="arugula", quantity=30, unit="g"),
        RecipeIngredient(recipe_id=salad.id, name="olive oil", quantity=10, unit="ml"),
    ]

    db.session.add_all(items)
    db.session.commit()
    print("sample created")