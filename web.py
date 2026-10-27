"""Painel privado de leitura do Gmail Digest."""
import hmac
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, session, redirect, url_for
from digest import fetch_messages, summarize
from daily_digest import period
from send_digest import important


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(32)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', '1') != '0',
                      MAX_CONTENT_LENGTH=8192)

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        configured = os.environ.get('DASHBOARD_PASSWORD', '')
        if not configured:
            return 'Configure DASHBOARD_PASSWORD no servidor para liberar o painel.', 503
        if request.method == 'POST':
            if hmac.compare_digest(request.form.get('password', '').encode(), configured.encode()):
                session.clear()
                session['authenticated'] = True
                return redirect(url_for('index'))
            error = 'Senha incorreta.'
        return render_template('login.html', error=error)

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    def index():
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        chosen = request.args.get('date', '')
        query = request.args.get('q', '').strip()[:200]
        only_important = request.args.get('important') == '1'
        messages, error, truncated = [], None, False
        try:
            start, end = period(chosen or None)
            messages, truncated = fetch_messages(24, 200, since=int(start.timestamp())-1, until=int(end.timestamp())+1)
            messages = [m for m in messages if m.get('received_at') and start.timestamp()*1000 <= int(m['received_at']) < end.timestamp()*1000]
            chosen = start.date().isoformat()
        except ValueError:
            error = 'Escolha uma data válida, até hoje.'
        except Exception:
            error = 'Não foi possível consultar o Gmail. Confira a autorização e a conexão do servidor.'
        total = len(messages)
        count_important = sum(important(m) for m in messages)
        cards = []
        for message in sorted(messages, key=lambda m: int(m.get('received_at') or 0), reverse=True):
            flagged = important(message)
            if only_important and not flagged:
                continue
            if query.casefold() not in (message['subject']+' '+message['sender']+' '+message['text']).casefold():
                continue
            cards.append(dict(message, summary=summarize(message['text']), flagged=flagged,
                hour=datetime.fromtimestamp(int(message['received_at'])/1000, ZoneInfo('America/Sao_Paulo')).strftime('%H:%M'),
                url='https://mail.google.com/mail/u/0/#all/'+message['id'] if re.fullmatch('[a-fA-F0-9]+', message['id']) else None))
        return render_template('dashboard.html', cards=cards, total=total, count_important=count_important,
            date=chosen, today=datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat(), q=query,
            only_important=only_important, error=error, truncated=truncated)
    return app


app = create_app()
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
