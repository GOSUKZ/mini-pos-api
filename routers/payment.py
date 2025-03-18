# 2. Добавьте роутер payment.py для обработки платежей

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from services.payment_service import PaymentService
from utils.dependencies import get_payment_service


router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/create")
async def create_payment(
    amount: float,
    currency: str = "USD",
    description: str = "",
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Создание платежа в PayPal."""
    try:
        order = await payment_service.create_order(amount, currency, description)

        # Извлекаем URL для перенаправления пользователя
        for link in order.get("links", []):
            if link["rel"] == "approve":
                return {"order_id": order["id"], "approve_url": link["href"]}

        raise HTTPException(status_code=500, detail="No approval URL found in PayPal response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/success")
async def payment_success(
    token: str, payment_service: PaymentService = Depends(get_payment_service)
):
    """Обработка успешного платежа."""
    try:
        # Получаем детали заказа
        order_details = await payment_service.get_order_details(token)

        # Завершаем платеж
        payment_result = await payment_service.capture_payment(token)

        # Здесь можно добавить логику обновления статуса заказа в вашей БД

        return {"status": "success", "order_id": token, "details": payment_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cancel")
async def payment_cancel():
    """Обработка отмененного платежа."""
    return {"status": "cancelled"}


@router.post("/webhook")
async def payment_webhook(request: Request):
    """Обработка уведомлений от PayPal."""
    payload = await request.json()

    # Здесь обрабатываем различные типы уведомлений
    event_type = payload.get("event_type")

    # Логика обработки различных типов событий
    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        # Платеж успешно завершен
        order_id = payload.get("resource", {}).get("id")
        # Обновление статуса заказа в БД
        pass

    return {"status": "webhook received"}
