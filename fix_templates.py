import os

# Fix grn_edit.html
grn_file = r'Templates\grn\grn_edit.html'
with open(grn_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all instances without spaces with spaces
content = content.replace('po.id==grn.po_id', 'po.id == grn.po_id')
content = content.replace('p.id==grn.product_id', 'p.id == grn.product_id')

with open(grn_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Fixed {grn_file}")

# Fix purchase_orders_edit.html
po_file = r'Templates\purchase_orders\purchase_orders_edit.html'
with open(po_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all instances without spaces with spaces
content = content.replace('s.id==po.supplier_id', 's.id == po.supplier_id')
content = content.replace("po.status=='pending'", "po.status == 'pending'")
content = content.replace("po.status=='approved'", "po.status == 'approved'")
content = content.replace("po.status=='rejected'", "po.status == 'rejected'")

with open(po_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Fixed {po_file}")
print("\nAll template files fixed! Restart the Django server.")
