# 1. Создайте новый файл сервиса payment_service.py

from fastapi import HTTPException
import httpx
from typing import Dict, Optional
import json


class PaymentService:
    def __init__(self):
        self.client_id = "ВАШ_PAYPAL_CLIENT_ID"
        self.client_secret = "ВАШ_PAYPAL_CLIENT_SECRET"
        self.base_url = "https://api-m.sandbox.paypal.com"  # Для тестирования, в продакшн используйте https://api-m.paypal.com

    async def get_access_token(self) -> str:
        """Получение access token для API PayPal."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"}
            )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get PayPal access token")

        return response.json().get("access_token")

    async def create_order(self, amount: float, currency: str = "USD", description: str = "") -> Dict:
        """Создание заказа в PayPal."""
        access_token = await self.get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": str(amount)
                    },
                    "description": description
                }
            ],
            "application_context": {
                "return_url": "http://localhost:8000/payment/success",
                "cancel_url": "http://localhost:8000/payment/cancel"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/checkout/orders",
                headers=headers,
                json=payload
            )

        if response.status_code not in (200, 201):
            raise HTTPException(status_code=400, detail=f"Failed to create PayPal order: {response.text}")

        return response.json()

    async def capture_payment(self, order_id: str) -> Dict:
        """Завершение оплаты после подтверждения пользователем."""
        access_token = await self.get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                headers=headers
            )

        if response.status_code not in (200, 201):
            raise HTTPException(status_code=400, detail=f"Failed to capture PayPal payment: {response.text}")

        return response.json()

    async def get_order_details(self, order_id: str) -> Dict:
        """Получение деталей заказа."""
        access_token = await self.get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v2/checkout/orders/{order_id}",
                headers=headers
            )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to get PayPal order details: {response.text}")

        return response.json()

