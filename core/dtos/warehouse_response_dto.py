"""
Модель ответа с информацией о складе.
"""

from pydantic import BaseModel

from core.models import Warehouse


class WarehouseResponseDTO(BaseModel):
    """Модель ответа с информацией о складе"""

    total_count: int
    current_page: int
    total_pages: int
    limit: int
    skip: int
    is_last: bool
    content: list[Warehouse]
