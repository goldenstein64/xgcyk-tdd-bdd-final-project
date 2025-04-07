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

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
from decimal import Decimal
from service.models import Product, Category, db, DataValidationError
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    def test_read_product(self):
        """It can read a product from the database"""
        product = ProductFactory()
        logging.debug(product)
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)

        found = Product.find(product.id)
        self.assertEqual(found, product)

    def test_update_product(self):
        """It can update a product in the database"""
        product = ProductFactory()
        logging.debug(product)
        product.id = None
        product.create()
        logging.debug(product)
        orig_id = product.id
        product.description = "cool description"
        product.update()
        found = Product.find(orig_id)
        self.assertEqual(orig_id, found.id)
        self.assertEqual("cool description", found.description)

    def test_delete_product(self):
        """It can delete a product from the database"""
        product = ProductFactory()
        product.create()
        self.assertEqual(len(Product.all()), 1)
        product.delete()
        self.assertEqual(len(Product.all()), 0)

    def test_list_all_products(self):
        """It can list all products in the database"""
        self.assertEqual(len(Product.all()), 0)
        for product in ProductFactory.create_batch(5):
            product.create()
        self.assertEqual(len(Product.all()), 5)

    def test_find_product_by_name(self):
        """It can find products in the database by name"""
        product = ProductFactory(name="cool name")
        for product in ProductFactory.create_batch(4):
            product.create()

        cool_products = sorted((p for p in Product.all() if p.name == "cool name"), key=lambda p: p.id)
        self.assertEqual(cool_products, sorted(Product.find_by_name("cool name"), key=lambda p: p.id))

    def test_find_product_by_price(self):
        """It can find products in the database by price"""
        product = ProductFactory(price=Decimal("12.50"))
        for product in ProductFactory.create_batch(4):
            product.create()

        products_1250 = sorted((p for p in Product.all() if p.price == Decimal("12.50")), key=lambda p: p.id)
        self.assertEqual(products_1250, sorted(Product.find_by_price("12.50")))
        self.assertEqual(products_1250, sorted(Product.find_by_price(" \" 12.50\"\"   ")))

    def test_find_product_by_availability(self):
        """It can find products in the database by availability"""
        for product in ProductFactory.create_batch(10):
            product.create()

        available = sorted((p for p in Product.all() if p.available is True), key=lambda p: p.id)
        unavailable = sorted((p for p in Product.all() if p.available is False), key=lambda p: p.id)
        self.assertEqual(available, sorted(Product.find_by_availability(), key=lambda p: p.id))
        self.assertEqual(available, sorted(Product.find_by_availability(True), key=lambda p: p.id))
        self.assertEqual(unavailable, sorted(Product.find_by_availability(False), key=lambda p: p.id))

    def test_find_product_by_category(self):
        """It can find products in the database by category"""
        for product in ProductFactory.create_batch(10):
            product.create()

        first_category = Product.all()[0].category
        categorized = sorted((p for p in Product.all() if p.category == first_category), key=lambda p: p.id)
        uncategorized = sorted((p for p in Product.all() if p.category == Category.UNKNOWN), key=lambda p: p.id)
        self.assertEqual(categorized, sorted(Product.find_by_category(first_category), key=lambda p: p.id))
        self.assertEqual(uncategorized, sorted(Product.find_by_category(), key=lambda p: p.id))

    def test_update_id_error(self):
        """Product updates error if the product's id is falsy"""
        product = ProductFactory()
        product.create()
        product.id = None
        with self.assertRaises(DataValidationError):
            product.update()

    def test_deserialize_available_error(self):
        """Deserializing a product errors if the 'available' field is non-boolean"""
        product = ProductFactory()
        product_dict = product.serialize()
        product_dict["available"] = 10
        with self.assertRaises(DataValidationError):
            product.deserialize(product_dict)

    def test_deserialize_category_error(self):
        """Deserializing a product errors if the 'category' field is not a valid category"""
        product = ProductFactory()
        product_dict = product.serialize()
        product_dict["category"] = "FAKE_CATEGORY"
        with self.assertRaises(DataValidationError):
            product.deserialize(product_dict)

    def test_deserialize_none_error(self):
        """Deserializing a non-product errors"""
        product = Product()
        with self.assertRaises(DataValidationError):
            product.deserialize(None)
