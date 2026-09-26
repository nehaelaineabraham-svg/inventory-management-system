import os
import shutil

# Read admin_layout.html and modify for manager
with open(r'Templates\admin\admin_layout.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace admin URLs with manager URLs
content = content.replace("{% url 'admin_dashboard' %}", "{% url 'manager_dashboard' %}")
content = content.replace("{% url 'logout' %}", "{% url 'manager_logout' %}")

# Modify sidebar - remove admin-only items, keep only manager-allowed items
# This is a simplified version - we'll create a custom sidebar for manager

# Save as manager_layout.html
with open(r'Templates\manager\manager_layout.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Created manager_layout.html")

# Copy admin.html as manager_dashboard.html
with open(r'Templates\admin\admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("{% extends 'admin/admin_layout.html' %}", "{% extends 'manager/manager_layout.html' %}")
content = content.replace("Admin Dashboard", "Manager Dashboard")

with open(r'Templates\manager\manager_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Created manager_dashboard.html")

print("\nAll manager templates created successfully!")
