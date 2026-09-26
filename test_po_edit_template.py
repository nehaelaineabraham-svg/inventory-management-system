import os
import django
from django.template import Context, Template
from django.template.loader import get_template

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')
django.setup()

from inventory import models

def test_template():
    print("Testing PO Edit Template Rendering...")
    
    # Mock Objects
    class MockProduct:
        def __init__(self, id, name, price):
            self.id = id
            self.product_name = name
            self.price = price
            
    class MockItem:
        def __init__(self, product_id, quantity, unit_price, total_price):
            self.product_id = product_id
            self.quantity = quantity
            self.unit_price = unit_price
            self.total_price = total_price
            
    p1 = MockProduct(101, "Test Prod 1", 100)
    p2 = MockProduct(102, "Test Prod 2", 200)
    producs = [p1, p2]
    
    item1 = MockItem(101, 5, 100, 500)
    items = [item1]
    
    # Simple Template Snippet simulating the loop
    template_str = """
    {% for item in items %}
        Row Item Product ID: {{ item.product_id }}
        Quantity: {{ item.quantity }}
        Dropdown:
        {% for p in products %}
            Option: {{ p.id }} - {{ p.product_name }} - {% if p.id == item.product_id %}SELECTED{% endif %}
        {% endfor %}
    {% empty %}
        EMPTY LIST
    {% endfor %}
    """
    
    t = Template(template_str)
    c = Context({"items": items, "products": producs})
    rendered = t.render(c)
    print(rendered)
    
    if "SELECTED" in rendered and "Option: 101" in rendered:
        print("PASS: Template logic works for matching IDs.")
    else:
        print("FAIL: Template logic failed to match IDs.")

if __name__ == "__main__":
    test_template()
