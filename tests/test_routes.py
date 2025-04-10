######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import db, init_db, Product, Category
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_product(self):
        """It can get a product by its id"""
        product = ProductFactory()
        product.create()
        response = self.client.get(f"/products/{product.id}")
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(product.serialize(), response.get_json())

    def test_get_product_not_found(self):
        """It returns a 404 status if the product does not exist"""
        response = self.client.get("/products/71077345")
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_update_product(self):
        """It can update a product in the database"""
        product = ProductFactory()
        product.create()
        response = self.client.put(f"/products/{product.id}", json={
            "name": "cool name",
            "description": "cool description",
        })
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        found_product = Product.find(product.id)
        self.assertEqual("cool name", found_product.name)
        self.assertEqual("cool description", found_product.description)

    def test_update_product_not_found(self):
        """It errors when trying to update a product that does not exist"""
        response = self.client.put("/products/71077345")
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_update_product_bad_json(self):
        """It errors when updating a product with a bad JSON body"""
        product = ProductFactory()
        product.create()
        response = self.client.put(f"/products/{product.id}", data="{")
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_update_product_empty_json(self):
        """It errors when updating a product with an empty JSON body"""
        product = ProductFactory()
        product.create()
        response = self.client.put(f"/products/{product.id}", json={})
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

    def test_update_product_bad_field_key(self):
        """It errors when updating a product using a bad field key"""
        product = ProductFactory()
        product.create()
        response = self.client.put(f"/products/{product.id}", json={"bad_field": "a"})
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

    def test_update_product_bad_field_value(self):
        """It errors when updating a product using a bad field value"""
        product = ProductFactory()
        product.create()
        response = self.client.put(f"/products/{product.id}", json={"available": 10})
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

    def test_delete_product(self):
        """It can delete a product"""
        product = ProductFactory()
        product.create()
        response = self.client.delete(f"/products/{product.id}")
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        no_product = Product.find(product.id)
        self.assertIsNone(no_product)

    def test_delete_product_not_found(self):
        """It errors when attempting to delete a product that does not exist"""
        response = self.client.delete("/products/71077345")
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_list_products(self):
        """It can list all products"""
        for product in ProductFactory.create_batch(10):
            product.create()

        response = self.client.get("/products")
        products = sorted((p.serialize() for p in Product.all()), key=lambda p: p["id"])
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(products, response.get_json())

    def test_list_products_by_name(self):
        """It can list products by name"""
        product = ProductFactory(name="cool name")
        product.create()
        for product in ProductFactory.create_batch(9):
            product.create()

        response = self.client.get("/products?name=cool%20name")
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        expected_body = sorted((p.serialize() for p in Product.find_by_name("cool name")), key=lambda p: p["id"])
        self.assertEqual(expected_body, sorted(response.get_json(), key=lambda p: p["id"]))

    def test_list_products_by_name_empty(self):
        """It errors when listing products with an empty name"""
        response = self.client.get("/products?name=")
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_list_products_by_category(self):
        """It can list products by category"""
        product = ProductFactory(category=Category.HOUSEWARES)
        product.create()
        for product in ProductFactory.create_batch(9):
            product.create()

        response = self.client.get("/products?category=HOUSEWARES")
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected_body = sorted((p.serialize() for p in Product.find_by_category(Category.HOUSEWARES)), key=lambda p: p["id"])
        self.assertEqual(expected_body, sorted(response.get_json(), key=lambda p: p["id"]))

    def test_list_products_by_bad_category(self):
        """It errors when listing products with a bad category query"""
        response = self.client.get("/products?category=FAKE_CATEGORY")
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_list_products_by_availability(self):
        """It can list products by availability"""
        for product in ProductFactory.create_batch(10):
            product.create()

        response = self.client.get("/products?available=false")
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected_body = sorted((p.serialize() for p in Product.find_by_availability(False)), key=lambda p: p["id"])
        self.assertEqual(expected_body, sorted(response.get_json(), key=lambda p: p["id"]))

    def test_list_products_by_bad_availability(self):
        """It errors when listing products with a bad availability query"""
        response = self.client.get("/products?available=FAKE_AVAILABILITY")
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    ######################################################################
    # Utility functions
    ######################################################################
    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
