import os
import unittest
from unittest.mock import patch
from web import create_app
from daily_digest import period

class PanelTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'DASHBOARD_PASSWORD': 'test-password', 'COOKIE_SECURE': '0'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = create_app().test_client()

    def test_private_and_login(self):
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertIn(b'Senha incorreta', self.client.post('/login', data={'password':'wrong'}).data)
        self.assertEqual(self.client.post('/login', data={'password':'test-password'}).status_code, 302)

    @patch('web.fetch_messages')
    def test_real_filter_and_escape(self, fetch):
        start, _ = period()
        fetch.return_value = ([{'id':'abc123', 'subject':'<script>alert(1)</script>',
            'sender':'Ana', 'text':'Entrega até amanhã.', 'received_at':str(int(start.timestamp()*1000)),
            'important':True, 'promotion':False}], False)
        self.client.post('/login', data={'password':'test-password'})
        response = self.client.get('/?q=Entrega&important=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertNotIn(b'<script>', response.data)
        self.assertIn(b'abc123', response.data)
        self.assertNotIn(b'abc123', self.client.get('/?q=ausente').data)
        self.client.post('/logout')
        self.assertEqual(self.client.get('/').status_code, 302)

    @patch('web.fetch_messages', side_effect=RuntimeError('secret-token'))
    def test_error_hides_secrets(self, fetch):
        self.client.post('/login', data={'password':'test-password'})
        response = self.client.get('/')
        self.assertNotIn(b'secret-token', response.data)
        self.assertIn(b'Cache-Control', str(response.headers).encode())
