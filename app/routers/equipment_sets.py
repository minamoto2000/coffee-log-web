from fastapi import APIRouter

from app.schemas.equipment_sets import EquipmentSetCreate, EquipmentSetRead, EquipmentSetUpdate
from app.services import equipment_sets as service

router = APIRouter(prefix="/equipment-sets", tags=["equipment-sets"])


@router.post("", status_code=201)
def create_equipment_set(data: EquipmentSetCreate) -> EquipmentSetRead:
    return service.create(data)


@router.get("")
def list_equipment_sets() -> list[EquipmentSetRead]:
    return service.list_active()


@router.get("/{equipment_set_id}")
def get_equipment_set(equipment_set_id: int) -> EquipmentSetRead:
    return service.get_active(equipment_set_id)


@router.patch("/{equipment_set_id}")
def update_equipment_set(equipment_set_id: int, data: EquipmentSetUpdate) -> EquipmentSetRead:
    return service.update(equipment_set_id, data)


@router.delete("/{equipment_set_id}")
def delete_equipment_set(equipment_set_id: int) -> EquipmentSetRead:
    """Soft delete: sets is_active = false. Past brew log snapshots are kept."""
    return service.deactivate(equipment_set_id)
