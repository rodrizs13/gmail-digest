import base64
import unittest
from digest import plain_text, render, summarize

class DigestTests(unittest.TestCase):
    def test_mime_prefers_plain(self):
        def part(mime, text):
            return {"mimeType": mime, "body": {"data": base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")}}
        payload = {"parts": [part("text/html", "<b>Outro texto</b>"),
                             {"parts": [part("text/plain", "Prazo amanhã.")]}]}
        self.assertEqual(plain_text(payload), "Prazo amanhã.")

    def test_html_removes_script(self):
        data = base64.urlsafe_b64encode(b'<script>secret()</script><p>Oi &amp; ola</p>').decode()
        self.assertEqual(plain_text({"mimeType":"text/html", "body":{"data":data}}), "Oi & ola")

    def test_action_sentence(self):
        self.assertEqual(summarize("Olá. Responda até amanhã. Obrigado."), "Responda até amanhã.")

    def test_empty_and_truncation(self):
        self.assertIn("Nenhuma mensagem", render([], 24))
        self.assertIn("Limite atingido", render([], 24, True))

    def test_promotion_is_grouped(self):
        message = {"id":"demo", "sender":"x", "subject":"Oferta secreta", "text":"oferta", "promotion":True}
        result = render([message], 24)
        self.assertNotIn("Oferta secreta", result)
        self.assertIn("Promoções agrupadas: 1", result)

if __name__ == "__main__":
    unittest.main()
