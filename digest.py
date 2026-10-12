"""Gmail Digest: resumo extrativo local, sem enviar conteúdo para uma IA."""
import argparse
import base64
import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def plain_text(payload):
    """Prefere texto simples; aceita HTML e partes MIME aninhadas."""
    collected = {"text/plain": [], "text/html": []}
    def walk(part):
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if mime in collected and data:
            decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
            collected[mime].append(decoded.decode("utf-8", errors="replace"))
        for child in part.get("parts", []):
            walk(child)
    walk(payload)
    text = " ".join(collected["text/plain"])
    if not text:
        text = " ".join(collected["text/html"])
        text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def summarize(text, limit=420):
    """Seleciona frases com possíveis ações/prazos, preservando o texto original."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    useful = [s for s in sentences if re.search(
        r"prazo|até|vencimento|respon|confirm|reunião|entrega|entrevista", s, re.I)]
    excerpt = " ".join((useful or sentences)[:2])
    return excerpt if len(excerpt) <= limit else excerpt[:limit].rstrip() + "…"


def normalize(message):
    payload = message.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    return {"id": message["id"], "sender": headers.get("from", "Desconhecido"),
            "subject": headers.get("subject", "Sem assunto"),
            "text": plain_text(payload) or html.unescape(message.get("snippet", "")),
            "promotion": "CATEGORY_PROMOTIONS" in message.get("labelIds", [])}


def fetch_messages(hours, maximum):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    raw = os.environ.get("GMAIL_TOKEN_JSON")
    info = json.loads(raw) if raw else json.loads(Path("token.json").read_text())
    creds = Credentials.from_authorized_user_info(info, SCOPES)
    if not creds.valid:
        if not creds.refresh_token:
            raise RuntimeError("Execute python authorize.py novamente.")
        creds.refresh(Request())
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    cutoff = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    query = f"after:{cutoff} -in:spam -in:trash -in:sent -in:drafts"
    messages, page = [], None
    while len(messages) < maximum:
        result = service.users().messages().list(userId="me", q=query,
            maxResults=min(100, maximum - len(messages)), pageToken=page).execute(num_retries=3)
        for entry in result.get("messages", []):
            message = service.users().messages().get(userId="me", id=entry["id"],
                format="full").execute(num_retries=3)
            messages.append(normalize(message))
        page = result.get("nextPageToken")
        if not page:
            break
    return messages, bool(page)


def render(messages, hours, truncated=False):
    def safe(value):
        return html.escape(value).replace("\n", " ").replace("\r", " ")
    lines = ["# Gmail Digest", "", f"Janela: últimas {hours} horas.", "",
             "Resumo extrativo: os trechos vêm das mensagens. Sinais de ação não são confirmação de urgência.", ""]
    promotions = sum(m["promotion"] for m in messages)
    for m in messages:
        if m["promotion"]:
            continue
        signals = bool(re.search(r"prazo|vencimento|respon|confirm|entrega", m["text"], re.I))
        lines += [f"## {safe(m['subject'])}", f"**De:** {safe(m['sender'])}", "",
                  safe(summarize(m["text"])) or "Sem texto disponível.", ""]
        if signals:
            lines += ["**Atenção:** há menção a prazo ou ação; confira a mensagem original.", ""]
        if re.fullmatch(r"[a-fA-F0-9]+", m["id"]):
            lines += [f"[Abrir no Gmail](https://mail.google.com/mail/u/0/#all/{m['id']})", ""]
    if not messages:
        lines += ["Nenhuma mensagem nova nessa janela.", ""]
    lines += [f"Promoções agrupadas: {promotions}."]
    if truncated:
        lines += ["Limite atingido: existem mais mensagens. Aumente --max-messages."]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--max-messages", type=int, default=200)
    parser.add_argument("--output", default="output/resumo.md")
    args = parser.parse_args()
    if args.hours < 1 or args.max_messages < 1:
        parser.error("Os limites devem ser maiores que zero.")
    if args.demo:
        messages = json.loads((Path(__file__).parent / "demo.json").read_text(encoding="utf-8"))
        truncated = False
    else:
        messages, truncated = fetch_messages(args.hours, args.max_messages)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(messages, args.hours, truncated), encoding="utf-8")
    print(f"Resumo gerado: {output}. Mensagens processadas: {len(messages)}.")


if __name__ == "__main__":
    main()
