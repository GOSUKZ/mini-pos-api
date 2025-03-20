"""
Module for service factory.

This module provides a class for creating and managing services.
The services are created on demand and stored in the instance.
"""

from services.auth_service import AuthService
from services.database.base import DatabaseService
from services.database.products import ProductsDataService
from services.database.receipt import ReceiptDataService
from services.database.sales import SalesDataService
from services.database.user import UsersDataService
from services.database.warehouse import WarehousesDataService
from services.product_service import ProductService
from services.sales_service import SalesService
from services.warehouse_service import WarehouseService


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

        self._auth_service = None
        self._sales_service = None
        self._warehouse_service = None
        self._product_service = None

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

    def get_auth_service(self):
        """
        Returns an instance of AuthService.

        This method ensures that a single instance of AuthService is created
        and reused. If the instance does not already exist, it is created using
        the provided database connection.

        Returns:
            AuthService: The instance of the auth service.
        """
        if not self._auth_service:
            self._auth_service = AuthService(self.get_auth_data_service())
        return self._auth_service

    def get_sales_service(self):
        """
        Returns an instance of SalesService.

        This method ensures that a single instance of SalesService is created
        and reused. If the instance does not already exist, it is created using
        the provided database connection.

        Returns:
            SalesService: The instance of the sales service.
        """
        if not self._sales_service:
            self._sales_service = SalesService(self.get_sales_data_service())
        return self._sales_service

    def get_warehouse_service(self):
        """
        Returns the warehouse service instance.

        This method ensures that a single instance of WarehouseService is created
        and reused. If the instance does not already exist, it is created using
        the provided database connection.

        Returns:
            WarehouseService: The instance of the warehouse service.
        """
        if not self._warehouse_service:
            self._warehouse_service = WarehouseService(self.get_warehouse_data_service())
        return self._warehouse_service

    def get_product_service(self):
        """
        Returns the product service instance.

        This method ensures that a single instance of ProductService is created
        and reused. If the instance does not already exist, it is created using
        the provided database connection.

        Returns:
            ProductService: The instance of the product service.
        """
        if not self._product_service:
            self._product_service = ProductService(self.get_product_data_service())
        return self._product_service
