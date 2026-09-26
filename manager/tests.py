from django.test import TestCase, Client
from django.urls import reverse
from inventory import models
import datetime

class ManagerDashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Mock session for manager
        session = self.client.session
        session['usertype'] = 'manager'
        session['name'] = 'Test Manager'
        session['user_id'] = 1
        session.save()

    def test_dashboard_view_status(self):
        response = self.client.get(reverse('manager_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_context_data(self):
        response = self.client.get(reverse('manager_dashboard'))
        self.assertIn('total_products', response.context)
        self.assertIn('total_suppliers', response.context)
        self.assertIn('total_pos', response.context)
        self.assertIn('total_grns', response.context)
        self.assertIn('total_sales', response.context)
        self.assertIn('recent_pos', response.context)
        self.assertIn('low_stock_products', response.context)
        self.assertIn('total_revenue', response.context)
        self.assertIn('monthly_revenue', response.context)
        self.assertIn('sales_labels', response.context)
        self.assertIn('sales_data', response.context)
