"""
Модель ответа с информацией о продажах.
"""

from pydantic import BaseModel

from core.models import Sale


class SaleResponseDTO(BaseModel):
    """Модель ответа с информацией о продаже"""

    total_count: int
    current_page: int
    total_pages: int
    limit: int
    skip: int
    is_last: bool
    content: list[Sale]
