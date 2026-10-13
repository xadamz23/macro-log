from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.deps import DB
from app.forms import form_values, parse_macro_form, parse_text
from app.services.foods import (
    create_quick_food,
    delete_quick_food,
    get_quick_food,
    list_quick_foods,
    move_quick_food,
    update_quick_food,
)
from app.templating import templates

router = APIRouter()


def _food_or_404(db, food_id: int):
    food = get_quick_food(db, food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Quick food not found")
    return food


def _parse(data) -> tuple[dict, dict, object]:
    form = parse_macro_form(data)
    name, name_error = parse_text(data, "name", max_len=100, required=True)
    label, label_error = parse_text(data, "serving_label", max_len=50)
    errors = dict(form.errors)
    if name_error:
        errors["name"] = name_error
    if label_error:
        errors["serving_label"] = label_error
    return {**form.values, "name": name, "serving_label": label}, errors, form.macros


def _list(request: Request, db, *, oob: bool = False, status_code: int = 200):
    return templates.TemplateResponse(
        request, "partials/food_list.html", {"foods": list_quick_foods(db), "oob": oob}, status_code=status_code
    )


@router.get("/settings/foods", response_class=HTMLResponse)
def foods_page(request: Request, db: DB):
    context = {"nav": "foods", "foods": list_quick_foods(db), "values": {}, "errors": {}, "prefix": "add"}
    return templates.TemplateResponse(request, "foods.html", context)


@router.get("/quick-foods", response_class=HTMLResponse)
def food_list(request: Request, db: DB):
    return _list(request, db)


@router.post("/quick-foods", response_class=HTMLResponse)
async def add_food(request: Request, db: DB):
    values, errors, macros = _parse(await request.form())
    if errors:
        context = {"values": values, "errors": errors, "prefix": "add"}
        return templates.TemplateResponse(request, "partials/food_add.html", context, status_code=422)
    create_quick_food(db, name=values["name"], serving_label=values["serving_label"], macros=macros)
    context = {"values": {}, "errors": {}, "prefix": "add", "foods": list_quick_foods(db), "oob": True, "with_list": True}
    return templates.TemplateResponse(request, "partials/food_add.html", context)


@router.get("/quick-foods/{food_id}/edit", response_class=HTMLResponse)
def edit_food_form(food_id: int, request: Request, db: DB):
    food = _food_or_404(db, food_id)
    values = {**form_values(food.macros), "name": food.name, "serving_label": food.serving_label}
    return templates.TemplateResponse(request, "partials/food_edit.html", {"food": food, "values": values, "errors": {}})


@router.put("/quick-foods/{food_id}", response_class=HTMLResponse)
async def update_food(food_id: int, request: Request, db: DB):
    food = _food_or_404(db, food_id)
    values, errors, macros = _parse(await request.form())
    if errors:
        return templates.TemplateResponse(
            request, "partials/food_edit.html", {"food": food, "values": values, "errors": errors},
            status_code=422, headers={"HX-Retarget": f"#food-{food.id}", "HX-Reswap": "outerHTML"},
        )
    update_quick_food(db, food, name=values["name"], serving_label=values["serving_label"], macros=macros)
    return _list(request, db)


@router.delete("/quick-foods/{food_id}", response_class=HTMLResponse)
def remove_food(food_id: int, request: Request, db: DB):
    delete_quick_food(db, _food_or_404(db, food_id))
    return _list(request, db)


@router.post("/quick-foods/{food_id}/move", response_class=HTMLResponse)
def move_food(food_id: int, request: Request, db: DB, direction: str = "up"):
    if direction not in ("up", "down"):
        raise HTTPException(status_code=422, detail="direction must be up or down")
    move_quick_food(db, _food_or_404(db, food_id), direction)
    return _list(request, db)
