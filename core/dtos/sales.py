from pydantic import BaseModel


class CreateSaleResponseDTO(BaseModel):
    order_id: str


class SaleMessageResponseDTO(BaseModel):
    order_id: str
    message: str
