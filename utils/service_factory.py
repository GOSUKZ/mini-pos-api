"""
Module for service factory.

This module provides a class for creating and managing services.
The services are created on demand and stored in the instance.
"""

from services.database.base import DatabaseService
from services.database.products import ProductsDataService
from services.database.receipt import ReceiptDataService
from services.database.sales import SalesDataService
from services.database.user import UsersDataService
from services.database.warehouse import WarehousesDataService


class ServiceFactory:
    """
    Класс для создания сервисов.

    Используется для создания сервисов на основе базы данных.
    """

    def __init__(self, db):
        """
        Инициализирует сервис-фабрику.

        Args:
            db: Экземпляр базы данных
        """
        self.db = db
        self._db_service = None
        self._auth_data_service = None
        self._warehouse_data_service = None
        self._product_data_service = None
        self._sales_data_service = None
        self._receipt_data_service = None

    def get_db_service(self):
        """
        Returns an instance of DatabaseService.

        This method ensures that a single instance of DatabaseService is created
        and reused. If the instance does not already exist, it is created using
        the provided database connection.

        Returns:
            DatabaseService: The instance of the database service.
        """
        if not self._db_service:
            self._db_service = DatabaseService(self.db)
        return self._db_service

    def get_auth_data_service(self):
        """
        Returns an instance of UsersDataService.

        This method ensures that a single instance of UsersDataService is created
        and reused. If the instance does not already exist, it is created using
        the provided database connection.

        Returns:
            UsersDataService: The instance of the users data service.
        """
        if not self._auth_data_service:
            self._auth_data_service = UsersDataService(self.db)
        return self._auth_data_service

    def get_warehouse_data_service(self):
        """
        Returns an instance of WarehousesDataService.

        This method ensures that a single instance of WarehousesDataService is created
        and reused. If the instance does not already exist, it is created using
        the provided database connection.

        Returns:
            WarehousesDataService: The instance of the warehouses data service.
        """
        if not self._warehouse_data_service:
            self._warehouse_data_service = WarehousesDataService(self.db)
        return self._warehouse_data_service

    def get_product_data_service(self):
        """
        Returns an instance of ProductsDataService.

        This method ensures that a single instance of ProductsDataService is created
        and reused. If the instance does not already exist, it is created using
        the provided database connection.

        Returns:
            ProductsDataService: The instance of the products data service.
        """
        if not self._product_data_service:
            self._product_data_service = ProductsDataService(self.db)
        return self._product_data_service

    def get_sales_data_service(self):
        """
        Returns an instance of SalesDataService.

        This method ensures that a single instance of SalesDataService is created
        and reused. If the instance does not already exist, it is created using
        the provided database connection.

        Returns:
            SalesDataService: The instance of the sales data service.
        """
        if not self._sales_data_service:
            self._sales_data_service = SalesDataService(self.db)
        return self._sales_data_service

    def get_receipt_data_service(self):
        """
        Returns an instance of ReceiptDataService.

        This method ensures that a single instance of ReceiptDataService is created
        and reused. If the instance does not already exist, it is created using
        the provided database connection.

        Returns:
            ReceiptDataService: The instance of the receipt data service.
        """
        if not self._receipt_data_service:
            self._receipt_data_service = ReceiptDataService(self.db)
        return self._receipt_data_service
