from pydantic import BaseModel


class TopProductDTO(BaseModel):
    product_id: int
    product_name: str
    product_price: float
    total_sold: int
