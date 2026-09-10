from django.test import TestCase

from rest_framework.test import APITestCase
from rest_framework import status

from .models import Category, Product, Customer, Order


class ProductModelTest(TestCase):

    def test_product_creation(self):
        category = Category.objects.create(
            name="Electronics"
        )

        product = Product.objects.create(
            category=category,
            name="Laptop",
            description="Test laptop",
            price="1000.00",
            stock=10
        )

        self.assertEqual(product.name, "Laptop")
        self.assertEqual(product.stock, 10)
        self.assertEqual(product.price, "1000.00")

class ProductAPITest(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics"
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Laptop",
            description="Test laptop",
            price="1000.00",
            stock=10
        )

    def test_get_products(self):
        response = self.client.get("/api/v1/products/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            len(response.data),
            1
        )

        self.assertEqual(
            response.data[0]["name"],
            "Laptop"
        )


    def test_create_product(self):
        data = {
            "category": self.category.id,
            "name": "Keyboard",
            "description": "Test keyboard",
            "price": "50.00",
            "stock": 20
        }

        response = self.client.post(
            "/api/v1/products/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.assertEqual(
            response.data["name"],
            "Keyboard"
        )

        self.assertEqual(
            response.data["stock"],
            20
        )

        self.assertEqual(
            Product.objects.count(),
            2
        )

    def test_create_product_with_negative_stock(self):
        data = {
            "category": self.category.id,
            "name": "Invalid Product",
            "description": "Should not be created",
            "price": "50.00",
            "stock": -1
        }

        response = self.client.post(
            "/api/v1/products/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_create_product_with_zero_price(self):
        data = {
            "category": self.category.id,
            "name": "Invalid Product",
            "description": "Should not be created",
            "price": "0.00",
            "stock": 10
        }

        response = self.client.post(
            "/api/v1/products/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )


class OrderAPITest(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics"
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Laptop",
            description="Test laptop",
            price="1000.00",
            stock=10
        )

        self.customer = Customer.objects.create(
            name="Test Customer",
            email="test@example.com",
            phone="0590000000"
        )

    def test_create_order_and_decrease_stock(self):
        data = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 2
                }
            ]
        }

        response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.assertEqual(
            response.data["customer"],
            self.customer.id
        )

        self.assertEqual(
            response.data["status"],
            "pending"
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            8
        )

        self.assertEqual(
            Order.objects.count(),
            1
        )

    def test_create_order_with_insufficient_stock(self):
        data = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 11
                }
            ]
        }

        response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            10
        )

        self.assertEqual(
            Order.objects.count(),
            0
        )

    def test_create_order_with_duplicate_products(self):
        data = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 2
                },
                {
                    "product_id": self.product.id,
                    "quantity": 3
                }
            ]
        }

        response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertIn(
            "A product cannot appear more than once in an order.",
            str(response.data)
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            10
        )

        self.assertEqual(
            Order.objects.count(),
            0
        )

    def test_cancel_order_and_restore_stock(self):
        data = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 2
                }
            ]
        }

        create_response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED
        )

        order_id = create_response.data["id"]

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            8
        )

        cancel_response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/{order_id}/cancel/",
            format="json"
        )

        self.assertEqual(
            cancel_response.status_code,
            status.HTTP_200_OK
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            10
        )

        self.assertEqual(
            cancel_response.data["status"],
            "cancelled"
        )

    def test_cancel_already_cancelled_order(self):
        data = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 2
                }
            ]
        }

        create_response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED
        )

        order_id = create_response.data["id"]

        cancel_url = (
            f"/api/v1/customers/{self.customer.id}"
            f"/orders/{order_id}/cancel/"
        )

        first_cancel_response = self.client.post(
            cancel_url,
            format="json"
        )

        self.assertEqual(
            first_cancel_response.status_code,
            status.HTTP_200_OK
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            10
        )

        second_cancel_response = self.client.post(
            cancel_url,
            format="json"
        )

        self.assertEqual(
            second_cancel_response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertIn(
            "Only pending orders can be cancelled.",
            str(second_cancel_response.data)
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            10
        )

    def test_get_customer_orders(self):
        data = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 2
                }
            ]
        }

        create_response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED
        )

        response = self.client.get(
            f"/api/v1/customers/{self.customer.id}/orders/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            len(response.data),
            1
        )

        self.assertEqual(
            response.data[0]["customer"],
            self.customer.id
        )

    def test_get_order_items(self):
        data = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 2
                }
            ]
        }

        create_response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED
        )

        order_id = create_response.data["id"]

        response = self.client.get(
            f"/api/v1/orders/{order_id}/items/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            len(response.data),
            1
        )

        self.assertEqual(
            response.data[0]["product_id"],
            self.product.id
        )

        self.assertEqual(
            response.data[0]["quantity"],
            2
        )

        self.assertEqual(
            response.data[0]["unit_price"],
            "1000.00"
        )

    def test_filter_products(self):
        response = self.client.get(
            f"/api/v1/products/?category={self.category.id}&in_stock=true"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            len(response.data),
            1
        )

        self.assertEqual(
            response.data[0]["id"],
            self.product.id
        )

    def test_filter_orders_by_status(self):
        data = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 2
                }
            ]
        }

        create_response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED
        )

        order_id = create_response.data["id"]

        cancel_response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/{order_id}/cancel/",
            format="json"
        )

        self.assertEqual(
            cancel_response.status_code,
            status.HTTP_200_OK
        )

        pending_order_response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            pending_order_response.status_code,
            status.HTTP_201_CREATED
        )

        response = self.client.get(
            "/api/v1/orders/?status=pending"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            len(response.data),
            1
        )

        self.assertEqual(
            response.data[0]["status"],
            "pending"
        )

    def test_cannot_update_order_with_patch(self):
        order = Order.objects.create(
            customer=self.customer,
            status=Order.Status.PENDING
        )

        response = self.client.patch(
            f'/api/v1/orders/{order.id}/',
            {
                'status': 'confirmed'
            },
            format='json'
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.PENDING
        )


    def test_cannot_update_order_with_put(self):
        order = Order.objects.create(
            customer=self.customer,
            status=Order.Status.PENDING
        )

        response = self.client.put(
            f'/api/v1/orders/{order.id}/',
            {
                'customer': self.customer.id,
                'status': 'confirmed'
            },
            format='json'
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.PENDING
        )

    def test_create_order_with_multiple_products(self):
        second_product = Product.objects.create(
            category=self.category,
            name="Keyboard",
            description="Test keyboard",
            price="80.00",
            stock=5
        )

        data = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 2
                },
                {
                    "product_id": second_product.id,
                    "quantity": 1
                }
            ]
        }

        response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        order = Order.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            order.items.count(),
            2
        )

        self.product.refresh_from_db()
        second_product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            8
        )

        self.assertEqual(
            second_product.stock,
            4
        )

        self.assertEqual(
            response.data["total"],
            "2080.00"
        )

    def test_order_keeps_historical_unit_price(self):
        data = {
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": 2
                }
            ]
        }

        response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        order_id = response.data["id"]

        self.product.price = "1200.00"
        self.product.save()

        response = self.client.get(
            f"/api/v1/orders/{order_id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["items"][0]["unit_price"],
            "1000.00"
        )

        self.assertEqual(
            response.data["total"],
            "2000.00"
        )

    def test_create_order_with_empty_items(self):
        data = {
            "items": []
        }

        response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertIn(
            "An order must contain at least one item.",
            str(response.data)
        )

        self.assertEqual(
            Order.objects.count(),
            0
        )

    def test_create_order_with_nonexistent_product(self):
        data = {
            "items": [
                {
                    "product_id": 9999,
                    "quantity": 1
                }
            ]
        }

        response = self.client.post(
            f"/api/v1/customers/{self.customer.id}/orders/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertIn(
            "Product with id 9999 does not exist.",
            str(response.data)
        )

        self.assertEqual(
            Order.objects.count(),
            0
        )