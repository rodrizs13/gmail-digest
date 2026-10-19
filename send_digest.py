"""Envio opcional de resumos. A prévia não envia nem altera o histórico."""
import argparse
import base64
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path

from digest import fetch_messages, gmail_service, summarize


def validate_recipient(address):
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", address):
        raise ValueError('Informe um único endereço de destino válido.')
    return address.lower()


def important(message, priority=()):
    if message.get('promotion') or '[gmail digest]' in message['subject'].lower():
        return False
    sender = parseaddr(message['sender'])[1].lower()
    return (message.get('important', False) or sender in priority or bool(re.search(
        r'\b(prazo|vencimento|responda|responder|confirme|confirmar|entrega|entrevista|reunião)\b',
        message['subject'] + ' ' + message['text'], re.I)))


def email_body(messages):
    lines = ['Resumo de mensagens possivelmente importantes',
             'Seleção por marcador Importante do Gmail, remetentes prioritários ou palavras-chave.',
             'Confira os originais: a seleção pode conter enganos.', '']
    for m in messages:
        lines.extend([m['subject'], 'De: ' + m['sender'], summarize(m['text'])])
        if re.fullmatch(r'[a-fA-F0-9]+', m['id']):
            lines.append('https://mail.google.com/mail/u/0/#all/' + m['id'])
        lines.append('')
    return '\n'.join(lines)


def encode_email(sender, recipient, body, count, html_body=None, subject=None):
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = validate_recipient(recipient)
    msg['Subject'] = subject or f'[Gmail Digest] {count} mensagem(ns) para conferir'
    msg['Date'] = formatdate(localtime=False)
    msg['Message-ID'] = make_msgid()
    msg['Auto-Submitted'] = 'auto-generated'
    msg.set_content(body)
    if html_body is not None:
        msg.add_alternative(html_body, subtype="html")
    return base64.urlsafe_b64encode(msg.as_bytes()).decode('ascii')


def deliver_pending(db, service):
    # Persist sending BEFORE calling Gmail. An interrupted/uncertain send is never retried automatically.
    if db.execute("SELECT 1 FROM outbox WHERE status IN ('sending','uncertain')").fetchone():
        raise RuntimeError('Envio anterior sem confirmação. Confira Enviados no Gmail e consulte o README antes de tentar novamente.')
    for row_id, raw in db.execute("SELECT id,raw FROM outbox WHERE status='pending' ORDER BY id").fetchall():
        db.execute('BEGIN IMMEDIATE')
        changed = db.execute("UPDATE outbox SET status='sending' WHERE id=? AND status='pending'", (row_id,)).rowcount
        db.commit()
        if not changed:
            continue
        try:
            result = service.users().messages().send(userId='me', body={'raw': raw}).execute(num_retries=0)
        except Exception:
            db.execute("UPDATE outbox SET status='uncertain' WHERE id=?", (row_id,))
            raise RuntimeError('Envio sem confirmação. Confira Enviados; não haverá repetição automática.') from None
        db.execute("UPDATE outbox SET status='sent', gmail_id=?, raw='' WHERE id=?", (result['id'], row_id))
        print('Resumo enviado. ID Gmail:', result['id'])


def run(recipient, preview=False, demo=False, hours=24, maximum=200, database=None, priority=(), resolve=None):
    recipient = validate_recipient(recipient)
    if demo and not preview:
        raise ValueError('Demonstração exige --preview e nunca envia e-mails.')
    service = None if demo else gmail_service(send=not preview)
    if preview:
        if demo:
            messages = json.loads(Path(__file__).with_name('demo.json').read_text(encoding='utf-8'))
            truncated = False
        else:
            messages, truncated = fetch_messages(hours, maximum, service=service)
        if truncated:
            raise RuntimeError('Limite atingido; aumente --max-messages.')
        selected = [m for m in messages if important(m, priority)]
        path = Path('output/previa-email.txt')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Destino: ' + recipient + '\n\n' + email_body(selected), encoding='utf-8')
        print(f'Prévia: {path}. Selecionadas: {len(selected)}. Nada enviado; histórico intacto.')
        return
    sender = service.users().getProfile(userId='me').execute(num_retries=3)['emailAddress'].lower()
    key = hashlib.sha256((sender + ':' + recipient).encode()).hexdigest()[:16]
    path = Path(database or f'data/envio-{key}.sqlite3')
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY CHECK(id=1), sender TEXT, recipient TEXT, checkpoint INTEGER);
            CREATE TABLE IF NOT EXISTS processed (id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY, raw TEXT, status TEXT, gmail_id TEXT);
        ''')
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT OR IGNORE INTO config VALUES (1,?,?,NULL)', (sender, recipient))
        config = db.execute('SELECT sender,recipient,checkpoint FROM config').fetchone()
        if config[:2] != (sender, recipient):
            raise ValueError('Banco pertence a outra conta/destinatário. Use outro --database.')
        db.commit()
        if resolve:
            status = 'sent' if resolve == 'sent' else 'pending'
            db.execute("UPDATE outbox SET status=? WHERE status IN ('sending','uncertain')", (status,))
        deliver_pending(db, service)
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT checkpoint FROM config').fetchone()[0]
        checkpoint = int(datetime.now(timezone.utc).timestamp())
        cutoff = previous - 300 if previous is not None else checkpoint - hours * 3600
        messages, truncated = fetch_messages(hours, maximum, since=cutoff, service=service)
        if truncated:
            raise RuntimeError('Limite atingido; aumente --max-messages. Histórico não avançado.')
        seen = {r[0] for r in db.execute('SELECT id FROM processed')}
        fresh = []
        for m in messages:
            if m['id'] not in seen:
                fresh.append(m)
                seen.add(m['id'])
        selected = [m for m in fresh if important(m, priority)]
        if selected:
            raw = encode_email(sender, recipient, email_body(selected), len(selected))
            db.execute("INSERT INTO outbox(raw,status) VALUES (?,'pending')", (raw,))
        db.executemany('INSERT INTO processed VALUES (?)', [(m['id'],) for m in fresh])
        db.execute('UPDATE config SET checkpoint=?', (checkpoint,))
        db.commit()
        deliver_pending(db, service)
        if not selected:
            print('Nenhuma mensagem nova selecionada; nenhum novo e-mail enviado.')
    finally:
        if db.in_transaction:
            db.rollback()
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--to', required=True)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--hours', type=int, default=24)
    parser.add_argument('--max-messages', type=int, default=200)
    parser.add_argument('--database')
    parser.add_argument('--priority-sender', action='append', default=[])
    parser.add_argument('--resolve-uncertain', choices=['sent', 'retry'], help='Após verificar Enviados: sent confirma; retry pode duplicar')
    args = parser.parse_args()
    if args.hours < 1 or args.max_messages < 1:
        parser.error('Limites devem ser positivos.')
    try:
        run(args.to, args.preview, args.demo, args.hours, args.max_messages,
            args.database, tuple(x.lower() for x in args.priority_sender), args.resolve_uncertain)
    except (ValueError, RuntimeError, FileNotFoundError) as error:
        parser.exit(1, str(error) + '\n')
    except Exception as error:
        parser.exit(1, f'Falha ({type(error).__name__}). Confira autorização e conexão.\n')


if __name__ == '__main__':
    main()
