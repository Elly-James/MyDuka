import unittest
from unittest.mock import patch, MagicMock
from app import create_app
from flask_jwt_extended import create_access_token

class WorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Define user identities for mocking
        self.admin_identity = {'id': 1, 'role': 'ADMIN', 'store_id': 1}
        self.clerk_identity = {'id': 2, 'role': 'CLERK', 'store_id': 1}

        # Mock tokens
        self.admin_token = create_access_token(identity=self.admin_identity)
        self.clerk_token = create_access_token(identity=self.clerk_identity)

    def tearDown(self):
        self.app_context.pop()

    @patch('routes.inventory.get_jwt_identity')
    @patch('routes.inventory.socketio')
    @patch('routes.inventory.Notification')
    def test_full_inventory_workflow(self, mock_notification, mock_socketio, mock_get_jwt_identity):
        # Mock get_jwt_identity for clerk and admin
        mock_get_jwt_identity.side_effect = [self.clerk_identity, self.admin_identity]
        mock_socketio.emit = MagicMock()

        # Mock the inventory entry creation
        with patch('routes.inventory.Product') as MockProduct, \
             patch('routes.inventory.InventoryEntry') as MockEntry, \
             patch('routes.inventory.db') as MockDb:
            mock_product = MagicMock(id=1, store_id=1, current_stock=0)
            MockProduct.query.get.return_value = mock_product
            mock_entry = MagicMock(id=1)
            MockEntry.return_value = mock_entry
            MockDb.session.add = MagicMock()
            MockDb.session.commit = MagicMock()

            entry_res = self.client.post('/api/inventory/entries', json={
                'product_id': 1,
                'quantity_received': 10,
                'buying_price': 5.0,
                'selling_price': 8.0
            }, headers={'Authorization': f'Bearer {self.clerk_token}'})

        # Mock the payment status update
        with patch('routes.inventory.InventoryEntry') as MockEntry, \
             patch('routes.inventory.db') as MockDb:
            mock_entry = MagicMock(id=1, payment_status='UNPAID')
            MockEntry.query.get.return_value = mock_entry
            MockDb.session.commit = MagicMock()

            update_res = self.client.put(f'/api/inventory/update-payment/{entry_res.json["inventory_entry"]["id"]}', 
                                       json={'payment_status': 'PAID'},
                                       headers={'Authorization': f'Bearer {self.admin_token}'})

        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json['status'], 'success')
        self.assertEqual(update_res.json['inventory_entry']['payment_status'], 'PAID')

if __name__ == '__main__':
    unittest.main()