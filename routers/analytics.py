import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends

from core.dtos.sales import SalesAnalyticsDTO
from core.models import User
from utils.dependencies import get_current_user, get_services
from utils.service_factory import ServiceFactory

logger = logging.getLogger("product_router")

# Создаем роутер
router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    responses={404: {"description": "Not found"}},
)


@router.get("/sales", response_model=SalesAnalyticsDTO)
async def get_sales_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    services: ServiceFactory = Depends(get_services),
):
    """
    Получает аналитику продаж.
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(weeks=1)
    if end_date is None:
        end_date = datetime.now()

    print("START DATE", start_date)
    print("END DATE", end_date)
    analytics = await services.get_sales_service().get_sales_analytics(
        current_user.id, start_date, end_date
    )

    print(analytics["latest_orders"])

    if not analytics:
        return SalesAnalyticsDTO(
            average_invoice=0,
            latest_orders=[],
            paid_percentage=0,
            profit=0,
            sales_today=0,
            top_products=[],
            total_paid_sum=0,
            total_sales_count=0,
            total_sales_sum=0,
            total_unpaid_sum=0,
            unpaid_percentage=0,
        )

    analytics["latest_orders"] = json.loads(analytics["latest_orders"])
    analytics["top_products"] = json.loads(analytics["top_products"])

    analytics = SalesAnalyticsDTO(**analytics)

    return analytics
