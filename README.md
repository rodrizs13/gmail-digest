# Gmail Digest 

Automação em Python para transformar mensagens do Gmail em um relatório curto, destacando trechos com possíveis prazos e ações. Projeto de portfólio com OAuth 2.0, integração REST, tratamento MIME, testes e GitHub Actions.

## O que faz

- Busca mensagens recebidas nas últimas 24 horas, com paginação e limite configurável.
- Extrai texto simples ou HTML de mensagens MIME.
- Seleciona até duas frases relevantes por mensagem e agrupa promoções.
- Gera Markdown com remetente, assunto e link para o Gmail.
- Executa uma demonstração sem conta, dependências externas ou dados reais.
- Agenda execuções em repositórios privados pelo GitHub Actions.

**É um resumo extrativo por regras, não uma IA generativa.** Não entende todos os contextos nem garante identificar urgências. Anexos não são resumidos. Nenhuma mensagem é enviada, apagada ou marcada como lida.

## Teste agora — sem conectar Gmail

Requer Python 3.10 ou superior. Abra um terminal dentro desta pasta:

```bash
python digest.py --demo
python -m unittest discover -s tests -v
```

Abra `output/resumo.md`. Os exemplos usam endereços fictícios. Veja também [exemplo-resumo.md](exemplo-resumo.md).

## Ler seu Gmail de verdade

A conexão do Gmail no ChatGPT não fornece credenciais para este código. Autorize o projeto separadamente no seu computador:

1. Crie um projeto no [Google Cloud](https://console.cloud.google.com/) e ative a Gmail API.
2. Configure a tela de consentimento OAuth no Google Auth Platform. Durante testes, adicione sua conta como usuário de teste.
3. Crie um cliente OAuth do tipo **Aplicativo para computador**. Baixe o JSON e salve nesta pasta com o nome `credentials.json`.
4. No terminal, instale e autorize:

```bash
python -m venv .venv
```

No Windows (CMD):

```bat
.venv\Scripts\activate
```

No Linux/macOS:

```bash
source .venv/bin/activate
```

Depois:

```bash
python -m pip install -r requirements.txt
python authorize.py
python digest.py
```

O navegador abre para você escolher sua conta e conceder acesso somente de leitura. `token.json` fica no computador. Nunca publique esse arquivo ou `credentials.json`. O `.gitignore` já os exclui, mas confira os arquivos antes de cada envio.

Para ampliar a janela ou o limite:

```bash
python digest.py --hours 48 --max-messages 500
```

## Automação diária

O arquivo `.github/workflows/daily.yml` usa 11h17 UTC, equivalente a 08h17 em Brasília. O GitHub pode atrasar execuções: não é um serviço de horário garantido. A janela fixa de 24h também pode deixar lacunas se houver atrasos ou falhas; para histórico contínuo, evolua o projeto com um cursor persistente.

Para usar com mensagens reais:

1. Suba uma cópia para um **repositório privado**.
2. Vá a **Settings → Secrets and variables → Actions → New repository secret**.
3. Nome: `GMAIL_TOKEN_JSON`. Valor: conteúdo completo de seu `token.json`.
4. Ative o Actions e execute **Resumo diário privado → Run workflow** para testar.
5. Baixe o arquivo `resumo-gmail` na seção **Artifacts** da execução. Ele permanece por um dia. Pessoas com acesso ao repositório poderão acessar o relatório.

O workflow diário bloqueia execução em repositórios públicos. Para o portfólio público, publique o código e a demonstração fictícia: o CI não usa credenciais. O relatório deste código fica em arquivo; ele não chega automaticamente ao ChatGPT ou por e-mail.

Apps OAuth externos em modo de teste podem ter refresh tokens com validade de sete dias. Nesse caso, reautorize e atualize o secret. Uso em produção com escopos Gmail pode exigir verificação do Google, conforme o público e o tipo de aplicação.

## Subir no GitHub

Crie um repositório vazio no GitHub e, dentro desta pasta, execute:

```bash
git init
git add .
git status
git commit -m "Adiciona Gmail Digest com demo e automacao"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/gmail-digest.git
git push -u origin main
```

Troque `SEU-USUARIO` pelo seu usuário. Se já existir um repositório local, não repita `git init` nem a criação do remote.

## Estrutura

| Arquivo | Responsabilidade |
| --- | --- |
| `digest.py` | Busca, extração, resumo e relatório |
| `authorize.py` | Autorização local OAuth |
| `demo.json` | Mensagens fictícias |
| `tests/test_digest.py` | Testes de MIME e relatório |
| `.github/workflows/ci.yml` | Testes e demonstração pública |
| `.github/workflows/daily.yml` | Agendamento privado |

## Decisões e próximos passos

O resumo por regras mantém o projeto gratuito e simples de explicar. Paginação evita depender apenas da primeira página; o relatório informa quando o limite foi atingido. As chamadas de API usam tentativas adicionais para falhas transitórias. Os testes cobrem MIME aninhado, HTML, seleção de frases, promoções e limites.

Possíveis evoluções: cursor persistente para evitar duplicações/lacunas, painel web, classificação melhor de newsletters, envio opcional com autorização explícita e dependências travadas com hashes. As bibliotecas estão limitadas por versão principal, mas não há lockfile reproduzível.

## Referências

- [Gmail API: quickstart Python](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [OAuth 2.0: expiração de refresh tokens](https://developers.google.com/identity/protocols/oauth2#expiration)
- [GitHub Actions: eventos e agendamento](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [GitHub Actions: secrets](https://docs.github.com/en/actions/how-tos/administering-github-actions/sharing-workflows-secrets-and-runners-with-your-organization)

Licença: MIT. Este projeto é independente do Google.
