"""Resumo HTML de todas as mensagens importantes de uma data em Brasília."""
import argparse
import hashlib
import html
import json
import re
import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from digest import fetch_messages, gmail_service, summarize
from send_digest import validate_recipient, important, encode_email, deliver_pending


def clean(value):
    return re.sub('[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D\u20E3]', '', str(value)).strip()


def period(day=None, now=None):
    zone = ZoneInfo('America/Sao_Paulo')
    now = now or datetime.now(zone)
    now = now.astimezone(zone)
    chosen = date.fromisoformat(day) if day else now.date()
    if chosen > now.date():
        raise ValueError('Escolha hoje ou uma data passada.')
    start = datetime.combine(chosen, time.min, zone)
    end = min(datetime.combine(chosen + timedelta(days=1), time.min, zone), now)
    return start, end


def render_daily(messages, start, end):
    label = start.strftime('%d/%m/%Y')
    end_label = end.strftime('%H:%M') if end.date() == start.date() else '24:00'
    subtitle = f'Das 00:00 às {end_label} · Horário de Brasília'
    text = [f'Resumo diário — {label}', subtitle,
            f'{len(messages)} mensagem(ns) selecionada(s)', '']
    cards = []
    for m in messages:
        subject = clean(m['subject']) or 'Sem assunto'
        sender = clean(m['sender'])
        excerpt = clean(summarize(m['text'])) or 'Sem texto disponível.'
        received = m.get('received_at')
        hour = datetime.fromtimestamp(int(received)/1000, start.tzinfo).strftime('%H:%M') if received else ''
        url = 'https://mail.google.com/mail/u/0/#all/' + m['id'] if re.fullmatch(r'[a-fA-F0-9]+', m['id']) else None
        text.extend([subject, f'De: {sender}', f'Horário: {hour}' if hour else '', excerpt])
        if url:
            text.append(url)
        text.append('')
        button = (f'<a href="{url}" style="display:inline-block;background:#eef2ff;color:#303f91;text-decoration:none;padding:11px 16px;border-radius:6px;font-size:13px;font-weight:bold">Abrir no Gmail</a>' if url else '')
        cards.append(f'''<tr><td style="padding:24px 0;border-bottom:1px solid #e5e7eb;overflow-wrap:anywhere">
<p style="margin:0 0 8px;font-size:12px;color:#64748b">{html.escape(hour)}</p>
<h2 style="margin:0 0 9px;font-size:19px;line-height:1.4;color:#172033">{html.escape(subject)}</h2>
<p style="margin:0 0 14px;font-size:13px;line-height:1.6;color:#64748b">De: {html.escape(sender)}</p>
<p style="margin:0 0 18px;font-size:15px;line-height:1.75;color:#334155">{html.escape(excerpt)}</p>{button}</td></tr>''')
    if not messages:
        cards.append('<tr><td style="padding:28px 0;color:#64748b;line-height:1.7">Nenhuma mensagem importante selecionada para este período.</td></tr>')
    footer = 'Seleção por marcadores, remetentes prioritários e palavras-chave. Confira os originais: a seleção pode conter enganos. Anexos não foram analisados.'
    text.append(footer)
    document = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Resumo diário — {label}</title></head>
<body style="margin:0;padding:0;background:#f3f5f9;font-family:Arial,Helvetica,sans-serif">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f5f9"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#fff;border:1px solid #e5e7eb;border-radius:12px">
<tr><td style="padding:30px 24px;background:#17233c;border-radius:12px 12px 0 0">
<p style="margin:0 0 18px;color:#b8c8e5;font-size:11px;letter-spacing:2px">GMAIL DIGEST</p>
<h1 style="margin:0 0 8px;color:#fff;font-size:27px;line-height:1.3">Resumo diário</h1>
<p style="margin:0;color:#d1dbee;font-size:16px">{label}</p></td></tr>
<tr><td style="padding:22px 24px 0"><p style="margin:0 0 10px;color:#64748b;font-size:12px;line-height:1.6">{subtitle}</p>
<p style="margin:0;color:#17233c;font-size:15px;font-weight:bold">{len(messages)} mensagem(ns) para conferir</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="table-layout:fixed">{''.join(cards)}</table></td></tr>
<tr><td style="padding:24px;color:#64748b;font-size:12px;line-height:1.7">{footer}<br>Os links exigem acesso à conta de origem.</td></tr>
</table></td></tr></table></body></html>'''
    return '\n'.join(text), document


def run(recipient, preview=False, demo=False, day=None, maximum=500, database=None, priority=(), resolve=None):
    recipient = validate_recipient(recipient)
    start, end = period(day)
    if demo and not preview:
        raise ValueError('Use --demo com --preview; a demonstração nunca envia.')
    service = None if demo else gmail_service(send=not preview)
    if demo:
        messages = json.loads(Path(__file__).with_name('demo.json').read_text(encoding='utf-8'))
        truncated = False
    else:
        # after is exclusive: subtract a second to include mail received at midnight.
        messages, truncated = fetch_messages(24, maximum, since=int(start.timestamp())-1,
                                             until=int(end.timestamp())+1, service=service)
        messages = [m for m in messages if m.get('received_at') is not None and
                    start.timestamp()*1000 <= int(m['received_at']) < end.timestamp()*1000]
    if truncated:
        raise RuntimeError('Limite atingido. Aumente --max-messages para cobrir o dia inteiro.')
    selected = sorted((m for m in messages if important(m, priority)),
                      key=lambda m: int(m.get('received_at') or 0))
    text, document = render_daily(selected, start, end)
    output = Path('output')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'previa-diaria.html').write_text(document, encoding='utf-8')
    (output / 'previa-diaria.txt').write_text('Destino: '+recipient+'\n\n'+text, encoding='utf-8')
    if preview:
        print(f'Prévia: output/previa-diaria.html. Selecionadas: {len(selected)}. Nada enviado.')
        return
    sender = service.users().getProfile(userId='me').execute(num_retries=3)['emailAddress'].lower()
    account_key = hashlib.sha256((sender+':'+recipient).encode()).hexdigest()[:16]
    path = Path(database or f'data/diario-{account_key}.sqlite3')
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY CHECK(id=1), sender TEXT, recipient TEXT);
            CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY, raw TEXT, status TEXT, gmail_id TEXT);
            CREATE TABLE IF NOT EXISTS reports (fingerprint TEXT PRIMARY KEY, day TEXT);
        ''')
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT OR IGNORE INTO config VALUES (1,?,?)', (sender,recipient))
        if db.execute('SELECT sender,recipient FROM config').fetchone() != (sender,recipient):
            raise ValueError('Banco de outra conta ou destinatário; escolha outro --database.')
        db.commit()
        if resolve:
            db.execute("UPDATE outbox SET status=? WHERE status IN ('sending','uncertain')",
                       ('sent' if resolve=='sent' else 'pending',))
        deliver_pending(db, service)
        # Ignore the changing generation time: an unchanged daily selection is sent once.
        fingerprint = hashlib.sha256(json.dumps([start.date().isoformat(), selected], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM reports WHERE fingerprint=?', (fingerprint,)).fetchone():
            db.commit()
            print('Este resumo diário já foi enviado. Nenhuma repetição.')
            return
        raw = encode_email(sender, recipient, text, len(selected), html_body=document,
                           subject=f'[Gmail Digest] Resumo diário — {start:%d/%m/%Y}')
        db.execute("INSERT INTO outbox(raw,status) VALUES (?,'pending')", (raw,))
        db.execute('INSERT INTO reports VALUES (?,?)', (fingerprint,start.date().isoformat()))
        db.commit()
        deliver_pending(db, service)
    finally:
        if db.in_transaction:
            db.rollback()
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--to', required=True)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--date', help='YYYY-MM-DD; padrão: hoje em Brasília')
    parser.add_argument('--max-messages', type=int, default=500)
    parser.add_argument('--database')
    parser.add_argument('--priority-sender', action='append', default=[])
    parser.add_argument('--resolve-uncertain', choices=['sent','retry'])
    args = parser.parse_args()
    if args.max_messages < 1:
        parser.error('Limite deve ser positivo.')
    try:
        run(args.to, args.preview, args.demo, args.date, args.max_messages,
            args.database, tuple(x.lower() for x in args.priority_sender), args.resolve_uncertain)
    except (ValueError, RuntimeError, FileNotFoundError) as error:
        parser.exit(1, str(error)+'\n')
    except Exception as error:
        parser.exit(1, f'Falha ({type(error).__name__}). Confira dependências, conexão e autorização.\n')


if __name__ == '__main__':
    main()
