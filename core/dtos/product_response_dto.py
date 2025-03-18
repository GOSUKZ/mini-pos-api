from core.models import Product
from pydantic import BaseModel


class ProductResponseDTO(BaseModel):
    """Модель ответа с информацией о товаре и ссылкой на оплату"""

    total_count: int
    current_page: int
    total_pages: int
    limit: int
    skip: int
    is_last: bool
    content: list[Product]
