from contextlib import closing

from app.db import get_connection
from app.errors import EmptyUpdateError, NotFoundError
from app.repositories import equipment_sets as repository
from app.schemas.equipment_sets import EquipmentSetCreate, EquipmentSetRead, EquipmentSetUpdate

NOT_FOUND = "Equipment set not found"


def create(data: EquipmentSetCreate) -> EquipmentSetRead:
    with closing(get_connection()) as conn:
        with conn:
            equipment_set_id = repository.insert(conn, data.model_dump())
        return EquipmentSetRead(**dict(repository.find_by_id(conn, equipment_set_id)))


def list_active() -> list[EquipmentSetRead]:
    with closing(get_connection()) as conn:
        return [EquipmentSetRead(**dict(row)) for row in repository.list_active(conn)]


def get_active(equipment_set_id: int) -> EquipmentSetRead:
    with closing(get_connection()) as conn:
        row = repository.find_active_by_id(conn, equipment_set_id)
        if row is None:
            raise NotFoundError(NOT_FOUND)
        return EquipmentSetRead(**dict(row))


def update(equipment_set_id: int, data: EquipmentSetUpdate) -> EquipmentSetRead:
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise EmptyUpdateError("No fields to update")

    with closing(get_connection()) as conn:
        with conn:
            if repository.find_active_by_id(conn, equipment_set_id) is None:
                raise NotFoundError(NOT_FOUND)
            repository.update_fields(conn, equipment_set_id, updates)
        return EquipmentSetRead(**dict(repository.find_by_id(conn, equipment_set_id)))


def deactivate(equipment_set_id: int) -> EquipmentSetRead:
    with closing(get_connection()) as conn:
        with conn:
            if repository.find_active_by_id(conn, equipment_set_id) is None:
                raise NotFoundError(NOT_FOUND)
            repository.deactivate(conn, equipment_set_id)
        return EquipmentSetRead(**dict(repository.find_by_id(conn, equipment_set_id)))
