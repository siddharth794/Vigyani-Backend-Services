from flask import Blueprint, jsonify
from ..models.products import Products
import logging

logger = logging.getLogger(__name__)
products_bp = Blueprint('products', __name__)

@products_bp.route('/list', methods=['GET'])
def get_product_list():
    """Get all products"""
    try:
        products = Products.get_product_list()
        if not products:
            return jsonify({'message': 'No products found'}), 404

        product_list = []
        for product in products:
            # Build description list, filtering out None values
            description_list = []
            if product.first:
                description_list.append(product.first)
            if product.second:
                description_list.append(product.second)
            if product.third:
                description_list.append(product.third)
            if product.fourth:
                description_list.append(product.fourth)
            
            product_list.append({
                'id': product.id,
                'type': product.type,
                'month_amount': int(float(product.amount)),
                'month_credit': int(float(product.credit)),
                'year_credit': int(float(product.credit)) * 12,
                'year_amount': int(float(product.amount)) * 12 * 0.85,  # Assuming 15% discount for yearly subscription
                'description': description_list,
                'period': product.period
            })

        return jsonify({'products': product_list}), 200

    except Exception as e:
        logger.error(f"Error fetching product list: {str(e)}")
        return jsonify({'error': 'Failed to fetch products'}), 500