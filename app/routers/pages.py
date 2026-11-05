from fastapi import APIRouter, Request

from app.presentation import (
    AGITATION_METHOD_LABELS,
    EXTRACTION_STYLE_LABELS,
    METRIC_DISPLAY,
    STATUS_LABELS,
    STEP_TYPE_LABELS,
    warning_message,
)
from app.services import comparison as comparison_service
from app.services import equipment_sets as equipment_set_service
from app.services import experiments as experiment_service
from app.services import trials as trial_service
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


# ---- experiment pages (01b 9) ----------------------------------------------


@router.get("/pages/experiments")
def experiments_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="experiments.html",
        context={"experiments": experiment_service.list_all(), "status_labels": STATUS_LABELS},
    )


@router.get("/pages/experiments/new")
def new_experiment_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="experiment_form.html",
        context={
            "equipment_sets": equipment_set_service.list_active(),
            "extraction_style_labels": EXTRACTION_STYLE_LABELS,
            "step_type_labels": STEP_TYPE_LABELS,
            "agitation_method_labels": AGITATION_METHOD_LABELS,
        },
    )


@router.get("/pages/experiments/{experiment_id}")
def experiment_detail_page(request: Request, experiment_id: int):
    return templates.TemplateResponse(
        request=request,
        name="experiment_detail.html",
        context={
            "experiment": experiment_service.get(experiment_id),
            "status_labels": STATUS_LABELS,
            "step_type_labels": STEP_TYPE_LABELS,
            "agitation_method_labels": AGITATION_METHOD_LABELS,
            "extraction_style_labels": EXTRACTION_STYLE_LABELS,
        },
    )


@router.get("/pages/experiments/{experiment_id}/trials/new")
def new_trial_page(request: Request, experiment_id: int):
    return templates.TemplateResponse(
        request=request,
        name="trial_form.html",
        context={"experiment": experiment_service.get(experiment_id)},
    )


@router.get("/pages/experiments/{experiment_id}/comparison")
def comparison_page(request: Request, experiment_id: int, include_deviated: bool = False):
    return templates.TemplateResponse(
        request=request,
        name="comparison.html",
        context={
            "experiment": experiment_service.get(experiment_id),
            "comparison": comparison_service.get(experiment_id, include_deviated),
            "metric_display": METRIC_DISPLAY,
            "warning_message": warning_message,
        },
    )


@router.get("/pages/trials/{trial_id}")
def trial_detail_page(request: Request, trial_id: int):
    return templates.TemplateResponse(
        request=request,
        name="trial_detail.html",
        context={"trial": trial_service.get(trial_id)},
    )
