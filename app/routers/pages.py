from fastapi import APIRouter, Request

from app.services import equipment_sets as equipment_set_service
from app.templating import templates

router = APIRouter(include_in_schema=False)


@router.get("/")
def home_page(request: Request):
    return templates.TemplateResponse(request=request, name="home.html", context={})


@router.get("/pages/equipment-sets")
def equipment_sets_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="equipment_sets.html",
        context={"equipment_sets": equipment_set_service.list_active()},
    )


@router.get("/pages/equipment-sets/new")
def new_equipment_set_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="equipment_set_form.html",
        context={"equipment_set": None},
    )


@router.get("/pages/equipment-sets/{equipment_set_id}/edit")
def edit_equipment_set_page(request: Request, equipment_set_id: int):
    return templates.TemplateResponse(
        request=request,
        name="equipment_set_form.html",
        context={"equipment_set": equipment_set_service.get_active(equipment_set_id)},
    )
