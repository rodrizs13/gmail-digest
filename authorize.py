"""Execute localmente para autorizar seu próprio Gmail."""
import argparse
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from digest import SCOPES

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-email", action="store_true", help="Permitir envio de resumos")
    args = parser.parse_args()
    scopes = SCOPES + (["https://www.googleapis.com/auth/gmail.send"] if args.send_email else [])
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    path = Path("token.json")
    path.write_text(credentials.to_json(), encoding="utf-8")
    path.chmod(0o600)
    print("Autorização concluída. token.json é privado: não envie ao Git.")
