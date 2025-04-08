######################################################################
# Copyright 2016, 2022 John J. Rofrano. All Rights Reserved.
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

# spell: ignore Rofrano jsonify restx dbname
"""
Product Store Service with UI
"""
from decimal import Decimal
from dataclasses import dataclass
from typing import Iterable, Callable, Any, Optional

from flask import jsonify, request, abort
from flask import url_for  # noqa: F401 pylint: disable=unused-import
from service.models import Product, Category
from service.common import status  # HTTP Status Codes
from . import app


######################################################################
# H E A L T H   C H E C K
######################################################################
@app.route("/health")
def healthcheck():
    """Let them know our heart is still beating"""
    return jsonify(status=200, message="OK"), status.HTTP_200_OK


######################################################################
# H O M E   P A G E
######################################################################
@app.route("/")
def index():
    """Base URL for our service"""
    return app.send_static_file("index.html")


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################
def check_content_type(content_type):
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )


######################################################################
# C R E A T E   A   N E W   P R O D U C T
######################################################################
@app.route("/products", methods=["POST"])
def create_products():
    """
    Creates a Product
    This endpoint will create a Product based the data in the body that is posted
    """
    app.logger.info("Request to Create a Product...")
    check_content_type("application/json")

    data = request.get_json()
    app.logger.info("Processing: %s", data)
    product = Product()
    product.deserialize(data)
    product.create()
    app.logger.info("Product with new id [%s] saved!", product.id)

    message = product.serialize()

    #
    # Uncomment this line of code once you implement READ A PRODUCT
    #
    location_url = url_for("get_products", product_id=product.id, _external=True)
    return jsonify(message), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
# L I S T   A L L   P R O D U C T S
######################################################################
@dataclass
class ResponseError:
    """Stores response errors to differentiate them from product iterators"""
    body: str
    status: int = status.HTTP_400_BAD_REQUEST

    def as_response(self):
        """Returns a tuple that can be used as a server response"""
        return (self.body, self.status)


def filter_by_name(name: str) -> Iterable[Product]:
    """Validates raw_names, then filters products by them"""
    if name == "":
        return ResponseError(
            body="name must not be empty",
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Product.find_by_name(name)


def filter_by_category(category: str) -> Iterable[Product]:
    """Validates raw_categories, then filters products by them"""
    if category not in Category.__members__:
        return ResponseError(
            body=f"category '{category}' is not valid",
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Product.find_by_category(Category[category])


def filter_by_availability(available: str) -> Iterable[Product]:
    """Validates raw_availabilities, then filters products by them"""
    if available not in ("true", "false"):
        return ResponseError(
            body=f"available value '{available}' is not true or false",
            status=status.HTTP_400_BAD_REQUEST
        )

    return Product.find_by_availability(available == "true")


filters = (
    ("name", filter_by_name),
    ("category", filter_by_category),
    ("available", filter_by_availability),
)


@app.route("/products", methods=["GET"])
def list_products():
    """Responds with a list of products filterable by query"""
    products = Product.all()
    for key, filter_func in filters:
        if key not in request.args:
            continue

        products = filter_func(request.args.get(key))
        if isinstance(products, ResponseError):
            return products.as_response()

        return [p.serialize() for p in products]

    return [p.serialize() for p in Product.all()]


######################################################################
# R E A D   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["GET"])
def get_products(product_id: int):
    """Get product information"""
    product = Product.find(product_id)
    if product is None:
        return ("product not found", status.HTTP_404_NOT_FOUND)

    return product.serialize()


######################################################################
# U P D A T E   A   P R O D U C T
######################################################################
@dataclass
class Transform:
    """Holds a validator and a converter together for a specific product field"""
    matches: Callable[[Any], bool]
    converts: Optional[Callable[[Any], Any]] = None


updateable = {
    "name": Transform(matches=lambda x: isinstance(x, str)),
    "description": Transform(matches=lambda x: isinstance(x, str)),
    "available": Transform(matches=lambda x: isinstance(x, bool)),
    "price": Transform(matches=lambda x: isinstance(x, str), converts=Decimal),
    "category": Transform(matches=lambda x: x in Category.__members__, converts=Category.__getitem__),
}


@app.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id: int):
    """Updates a product's information"""
    product = Product.find(product_id)
    if product is None:
        return ("product not found", status.HTTP_404_NOT_FOUND)

    data = request.get_json()
    if len(data) <= 0:
        return ("body must be non-empty", status.HTTP_422_UNPROCESSABLE_ENTITY)

    for key, value in data.items():
        transform = updateable.get(key)
        if transform is None:
            return (f"key '{key}' is not a valid field", status.HTTP_422_UNPROCESSABLE_ENTITY)
        if not transform.matches(value):
            return (f"field '{key}' has an invalid value ({value})", status.HTTP_422_UNPROCESSABLE_ENTITY)

        converted = value if transform.converts is None else transform.converts(value)
        setattr(product, key, converted)

    product.update()
    return product.serialize()


######################################################################
# D E L E T E   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    """Deletes a product by its id"""
    product = Product.find(product_id)
    if product is None:
        return ("product not found", status.HTTP_404_NOT_FOUND)

    product.delete()
    return ("", status.HTTP_204_NO_CONTENT)
