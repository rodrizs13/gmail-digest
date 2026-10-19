import base64
import os
import tempfile
import unittest
from datetime import datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from daily_digest import period, render_daily, run
from send_digest import encode_email


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.zone = ZoneInfo('America/Sao_Paulo')
        self.start, self.end = period('2026-10-19', datetime(2026,10,19,20,8,tzinfo=self.zone))
        self.message = {'id':'abc123','sender':'Cliente <client@example.com>',
                        'subject':'Entrega <script>alert(1)</script>',
                        'text':'Confirme a entrega amanhã. 😀', 'promotion':False,
                        'received_at':str(int(self.start.timestamp()*1000))}

    def test_brasilia_day_boundaries(self):
        self.assertEqual(self.start.isoformat(), '2026-10-19T00:00:00-03:00')
        self.assertEqual(self.end.hour, 20)
        start, end = period('2026-10-18', self.end)
        self.assertEqual(end-start, __import__('datetime').timedelta(days=1))
        self.assertEqual(end.hour, 0)
        with self.assertRaises(ValueError):
            period('2026-10-20', self.end)

    def test_html_escape_no_emoji_and_multipart(self):
        text, document = render_daily([self.message],self.start,self.end)
        self.assertIn('&lt;script&gt;',document)
        self.assertNotIn('<script>', document)
        self.assertNotIn('😀', document+text)
        self.assertIn('00:00 às 20:08', document)
        raw = encode_email('owner@example.com','target@example.com',text,1,document)
        mail = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw))
        self.assertEqual(mail.get_body(preferencelist=('html',)).get_content_type(),'text/html')
        self.assertIsNotNone(mail.get_body(preferencelist=('plain',)))

    def test_full_day_not_incremental_and_repeat_skipped(self):
        service = MagicMock()
        service.users().getProfile().execute.return_value = {'emailAddress':'owner@example.com'}
        service.users().messages().send().execute.return_value = {'id':'sent123'}
        service.users().messages().send.reset_mock()
        yesterday = dict(self.message,id='old',received_at=str(int(self.start.timestamp()*1000)-1))
        tomorrow = dict(self.message,id='later',received_at=str(int(self.end.timestamp()*1000)))
        with tempfile.TemporaryDirectory() as directory:
            old_cwd=os.getcwd()
            os.chdir(directory)
            try:
                with patch('daily_digest.period',return_value=(self.start,self.end)), patch('daily_digest.gmail_service',return_value=service), patch('daily_digest.fetch_messages',return_value=([self.message,yesterday,tomorrow],False)) as fetch:
                    run('target@example.com')
                    run('target@example.com')
                    self.assertEqual(service.users().messages().send.call_count,1)
                    self.assertEqual(fetch.call_args.kwargs['since'],int(self.start.timestamp())-1)
                    self.assertEqual(fetch.call_args.kwargs['until'],int(self.end.timestamp())+1)
                    self.assertIn('1 mensagem(ns)',Path('output/previa-diaria.html').read_text())
                    # Later message leads to a new FULL daily report containing both messages.
                    fetch.return_value=([self.message,dict(self.message,id='abc124')],False)
                    run('target@example.com')
                    self.assertEqual(service.users().messages().send.call_count,2)
                    self.assertIn('2 mensagem(ns)',Path('output/previa-diaria.html').read_text())
            finally:
                os.chdir(old_cwd)
