from pydantic import BaseModel


class CreateSaleResponseDTO(BaseModel):
    order_id: str
