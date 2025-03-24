from datetime import datetime
from typing import List

from pydantic import BaseModel

from core.dtos.product import TopProductDTO


class OrderDTO(BaseModel):
    order_id: str
    total_amount: float
    status: str
    created_at: datetime


class CreateSaleResponseDTO(BaseModel):
    order_id: str


class SaleMessageResponseDTO(BaseModel):
    order_id: str
    message: str


class SalesAnalyticsDTO(BaseModel):
    total_sales_sum: float
    total_sales_count: int
    sales_today: int
    total_paid_sum: float
    paid_percentage: float
    total_unpaid_sum: float
    unpaid_percentage: float
    average_invoice: float
    profit: float
    latest_orders: List[OrderDTO]
    top_products: List[TopProductDTO]
