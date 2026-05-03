from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.recipe import Recipe, RecipeFermentable, RecipeHop, RecipeYeast, RecipeMisc
from app.schemas.recipe import RecipeCreate, RecipeUpdate, RecipeRead, RecipeSummary

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _apply_ingredients(db: Session, recipe: Recipe, data: RecipeCreate | RecipeUpdate):
    if data.fermentables is not None:
        recipe.fermentables = [RecipeFermentable(recipe_id=recipe.id, **f.model_dump()) for f in data.fermentables]
    if data.hops is not None:
        recipe.hops = [RecipeHop(recipe_id=recipe.id, **h.model_dump()) for h in data.hops]
    if data.yeasts is not None:
        recipe.yeasts = [RecipeYeast(recipe_id=recipe.id, **y.model_dump()) for y in data.yeasts]
    if data.miscs is not None:
        recipe.miscs = [RecipeMisc(recipe_id=recipe.id, **m.model_dump()) for m in data.miscs]


@router.get("/", response_model=List[RecipeSummary])
def list_recipes(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Recipe).offset(skip).limit(limit).all()


@router.post("/", response_model=RecipeRead, status_code=201)
def create_recipe(payload: RecipeCreate, db: Session = Depends(get_db)):
    recipe = Recipe(**payload.model_dump(exclude={"fermentables", "hops", "yeasts", "miscs"}))
    db.add(recipe)
    db.flush()  # get recipe.id before creating children
    _apply_ingredients(db, recipe, payload)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("/{recipe_id}", response_model=RecipeRead)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.put("/{recipe_id}", response_model=RecipeRead)
def update_recipe(recipe_id: int, payload: RecipeUpdate, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    scalar_fields = payload.model_dump(exclude={"fermentables", "hops", "yeasts", "miscs"}, exclude_unset=True)
    for field, value in scalar_fields.items():
        setattr(recipe, field, value)

    _apply_ingredients(db, recipe, payload)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    db.delete(recipe)
    db.commit()
