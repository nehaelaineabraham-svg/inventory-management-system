import os
import shutil

# Read manager_layout.html and modify for staff
with open(r'Templates\manager\manager_layout.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace manager URLs with staff URLs
content = content.replace("{% url 'manager_dashboard' %}", "{% url 'staff_dashboard' %}")
content = content.replace("{% url 'manager_logout' %}", "{% url 'staff_logout' %}")
content = content.replace("Manager Dashboard", "Staff Dashboard")

# Save as staff_layout.html
with open(r'Templates\staffpanel\staff_layout.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Created staff_layout.html")

# Copy manager_dashboard.html as staff_dashboard.html
with open(r'Templates\manager\manager_dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("{% extends 'manager/manager_layout.html' %}", "{% extends 'staffpanel/staff_layout.html' %}")
content = content.replace("Manager Dashboard", "Staff Dashboard")

with open(r'Templates\staffpanel\staff_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Created staff_dashboard.html")

print("\nAll staff templates base created successfully!")
