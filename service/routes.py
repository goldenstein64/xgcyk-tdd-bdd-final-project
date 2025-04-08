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
from dataclasses import dataclass
from decimal import Decimal

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
    location_url = url_for("get_product", product_id=product.id, _external=True)
    return jsonify(message), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
# L I S T   A L L   P R O D U C T S
######################################################################

@app.route("/products", methods=["GET"])
def list_products():
    request.query
    return [p.serialize() for p in Product.all()]

######################################################################
# R E A D   A   P R O D U C T
######################################################################

@app.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id: int):
    product = Product.find(product_id)
    if product is None:
        return ("product not found", status.HTTP_404_NOT_FOUND)

    return product.serialize()

######################################################################
# U P D A T E   A   P R O D U C T
######################################################################

class Transform:
    def __init__(self, matches, converts = None):
        self.matches = matches
        self.converts = converts

updateable = { 
    "name": Transform(lambda x: isinstance(x, str)), 
    "description": Transform(lambda x: isinstance(x, str)), 
    "available": Transform(lambda x: isinstance(x, bool)), 
    "price": Transform(matches=lambda x: isinstance(x, str), converts=Decimal),
    "category": Transform(matches=lambda x: x in Category.__members__, converts=Category.__getitem__)
}
@app.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id: int):
    product = Product.find(product_id)
    if product is None:
        return ("product not found", status.HTTP_404_NOT_FOUND)

    data = request.get_json()
    if not isinstance(data, dict):
        return ("body must be a JSON object", status.HTTP_400_BAD_REQUEST)
    elif len(data) <= 0:
        return ("body must be non-empty", status.HTTP_422_UNPROCESSABLE_ENTITY)

    for k, v in data.items():
        transform = updateable.get(k)
        if transform is None:
            return (f"key '{k}' is not a valid field", status.HTTP_422_UNPROCESSABLE_ENTITY)
        elif not transform.matches(v):
            return (f"field '{k}' has an invalid value ({v})", status.HTTP_422_UNPROCESSABLE_ENTITY)
        else:
            converted = v if transform.converts is None else transform.converts(v)
            setattr(product, k, converted)

    product.update()
    return product.serialize()
            



######################################################################
# D E L E T E   A   P R O D U C T
######################################################################

@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    product = Product.find(product_id)
    if product is None:
        return ("product not found", status.HTTP_404_NOT_FOUND)
    else:
        product.delete()
        return ("", status.HTTP_204_NO_CONTENT)