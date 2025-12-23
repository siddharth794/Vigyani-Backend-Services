from ..utils.db import db_connection
import json

class Products:
    def __init__(self, id=None, type=None, amount=None, credit=None, 
                 description=None, period=None, first=None, second=None,
                 third=None, fourth=None):
        self.id = id
        self.type = type
        self.amount = amount
        self.credit = credit
        self.description = description
        self.period = period
        
        # Set first, second, third, fourth from parameters
        self.first = first
        self.second = second
        self.third = third
        self.fourth = fourth
        
        # If description is JSON and first/second are not set, parse it and extract features
        # This handles the case where features are stored as JSON in the description field
        if description and self.first is None and self.second is None:
            try:
                desc_data = json.loads(description)
                if isinstance(desc_data, dict) and 'features' in desc_data:
                    features = desc_data['features']
                    self.first = features[0] if len(features) > 0 else None
                    self.second = features[1] if len(features) > 1 else None
                    self.third = features[2] if len(features) > 2 else None
                    self.fourth = features[3] if len(features) > 3 else None
            except (json.JSONDecodeError, TypeError, AttributeError):
                # If not JSON, keep as is
                pass

    @classmethod
    def get_product_list(cls):
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM products
                """)
                products = cursor.fetchall()
                return [cls(**product_data) for product_data in products]  
