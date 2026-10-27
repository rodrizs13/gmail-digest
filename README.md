# Gmail Digest

Automação em Python que organiza mensagens do Gmail e gera resumos com possíveis prazos, pedidos de resposta e outros assuntos importantes. Inclui painel web privado com Flask, histórico em SQLite, autorização OAuth 2.0 e envio de relatórios por e-mail.

O resumo diário reúne as mensagens selecionadas de uma data em um e-mail HTML com assunto, remetente, horário, trecho relevante e link para o original. O layout usa cores discretas e texto sem emojis.

## Funcionalidades

- Painel web com login por senha e consulta da conta Gmail autorizada.
- Filtros por data de Brasília, busca por conteúdo e seleção de importantes.
- Contadores e links para abrir as mensagens originais no Gmail.

- Leitura de mensagens pela Gmail API, com paginação e limite configurável.
- Extração de texto de mensagens simples, HTML e partes MIME aninhadas.
- Resumo extrativo: seleciona até duas frases do texto original.
- Seleção por marcador **Importante** do Gmail, remetentes prioritários ou palavras relacionadas a prazos e ações.
- Exclusão de promoções nos resumos enviados.
- Histórico local em SQLite para evitar reprocessamento.
- Relatório Markdown, envio incremental em texto e resumo diário em HTML.
- Prévia antes do envio e demonstração com mensagens fictícias.
- Testes automatizados e workflow de integração contínua no GitHub Actions.

A seleção usa regras e pode incluir ou ignorar mensagens incorretamente. Anexos não são analisados. Os comandos não apagam mensagens nem as marcam como lidas.

## Requisitos

- Python 3.10 ou superior.
- Uma conta Google e um projeto com a Gmail API ativada para usar mensagens reais.
- Armazenamento persistente para manter os bancos entre execuções.

## Instalação

```bash
git clone https://github.com/rodrizs13/gmail-digest.git
cd gmail-digest
python -m venv .venv
```

Ative o ambiente conforme seu terminal:

| Terminal | Comando |
| --- | --- |
| Windows — Git Bash | `source .venv/Scripts/activate` |
| Windows — CMD | `.venv\Scripts\activate` |
| Linux/macOS | `source .venv/bin/activate` |

```bash
python -m pip install -r requirements.txt
```

O pacote `tzdata` fornece os dados de fuso horário usados pelo resumo diário, inclusive no Windows.

## Demonstração sem conectar uma conta

```bash
python digest.py --demo
```

Abra `output/resumo.md`. A primeira execução processa três mensagens fictícias; as seguintes não repetem os mesmos registros. O relatório é substituído em cada execução.

Para visualizar o layout diário com dados fictícios:

```bash
python daily_digest.py --to destinatario@example.com --demo --preview
```

Abra `output/previa-diaria.html`. A demonstração não envia e-mails.

## Conectar o Gmail

1. Crie ou selecione um projeto no [Google Cloud Console](https://console.cloud.google.com/).
2. Ative a **Gmail API**.
3. Configure o aplicativo OAuth no **Google Auth Platform**. Em modo de teste, adicione a conta que será conectada aos usuários de teste.
4. Crie um cliente OAuth do tipo **Aplicativo para computador**.
5. Baixe o JSON, renomeie para `credentials.json` e coloque na raiz do projeto.
6. Autorize a conta pelo navegador:

```bash
python authorize.py
```

Esse comando concede acesso de leitura e cria `token.json`. Para permitir também o envio dos resumos, execute:

```bash
python authorize.py --send-email
```

O remetente dos resumos será a conta autorizada. Uma nova autorização substitui o `token.json` existente; preserve separadamente os tokens das contas que deseja continuar usando. A versão atual utiliza uma conta autorizada por vez.

## Resumo diário em HTML

### Conferir a prévia

```bash
python daily_digest.py --to destinatario@example.com --preview
```

Arquivos gerados:

- `output/previa-diaria.html`: prévia visual para abrir no navegador.
- `output/previa-diaria.txt`: versão em texto com o destinatário.

A prévia não envia e-mails nem altera o histórico de entrega.

### Enviar o resumo

```bash
python daily_digest.py --to destinatario@example.com
```

O período vai da meia-noite até o momento da execução em **America/Sao_Paulo**. Mensagens já processadas pelos outros comandos continuam fazendo parte do relatório da data.

Para consultar um dia anterior completo:

```bash
python daily_digest.py --to destinatario@example.com --date 2026-10-18
```

Para priorizar remetentes ou ampliar o limite:

```bash
python daily_digest.py --to destinatario@example.com --priority-sender cliente@example.com --max-messages 1000
```

`--priority-sender` pode ser repetido. Promoções continuam excluídas. Se o limite impedir a leitura do período completo, o programa interrompe a operação em vez de enviar um relatório parcial.

O envio inclui versões HTML e texto simples. Um período sem mensagens selecionadas gera um relatório informando essa ausência. O mesmo conjunto de mensagens da mesma data não é reenviado; se chegarem novas mensagens importantes, a próxima execução poderá enviar uma versão atualizada com o dia inteiro. Os links exigem acesso à caixa de origem.

## Outros modos de uso

| Comando | Comportamento |
| --- | --- |
| `python digest.py` | Gera `output/resumo.md` com mensagens ainda não processadas. |
| `python send_digest.py --to destinatario@example.com --preview` | Gera uma prévia em texto das mensagens importantes da janela consultada, sem enviar. |
| `python send_digest.py --to destinatario@example.com` | Envia somente mensagens importantes ainda não processadas pelo histórico de entrega incremental. |
| `python daily_digest.py --to destinatario@example.com` | Envia todas as mensagens importantes selecionadas da data, independentemente dos históricos incrementais. |

No relatório local e no envio incremental, `--hours` define a janela inicial, de 24 horas por padrão. Depois, o cursor persistente governa a busca, com cinco minutos de sobreposição. A prévia de `send_digest.py` consulta a janela indicada, sem aplicar o histórico de entrega.

## Histórico e recuperação de falhas

Os bancos padrão ficam em `data/`, separados por finalidade:

| Banco | Uso |
| --- | --- |
| `demo.sqlite3` | Demonstração do relatório local. |
| `gmail.sqlite3` | Mensagens e execuções do relatório local. |
| `envio-*.sqlite3` | Histórico e caixa de saída do envio incremental. |
| `diario-*.sqlite3` | Relatórios diários e caixa de saída. |

Todos os comandos reais aceitam `--database` para indicar outro caminho. Use um banco por conta; os bancos de envio também são vinculados ao destinatário. Mantenha os bancos em disco persistente e faça backup.

A caixa de saída salva o relatório antes de chamar o Gmail. Se o envio ficar sem confirmação, o programa bloqueia a repetição automática. Confira a pasta **Enviados** antes de resolver:

```bash
# Quando confirmou que o resumo já foi enviado:
python daily_digest.py --to destinatario@example.com --resolve-uncertain sent

# Para tentar novamente após conferir; pode causar duplicação:
python daily_digest.py --to destinatario@example.com --resolve-uncertain retry
```

As mesmas opções estão disponíveis em `send_digest.py`. Resolver um envio também continua o processamento normal de mensagens. Não apague o banco para contornar um bloqueio.

## Automação

Os comandos de envio são manuais nesta versão. O nome “diário” define o período do relatório; não cria um agendamento.

O workflow `.github/workflows/daily.yml` do repositório agenda **somente a geração do Markdown**, às 11h17 UTC, equivalentes a 08h17 em Brasília. Ele exige repositório privado e o secret `GMAIL_TOKEN_JSON`. Não executa os comandos de envio por e-mail.

**Limitação atual:** esse workflow usa um runner hospedado sem persistência do SQLite entre execuções. Para preservar o histórico em uma automação real, adapte a execução para armazenamento durável ou um runner próprio. Execuções agendadas também podem sofrer atrasos.

## Privacidade

Publique somente código, documentação e exemplos fictícios. Mantenha fora do Git:

```gitignore
credentials*.json
token*.json
.env
output/
data/
*.sqlite3
*.sqlite3-*
__pycache__/
.venv/
```

Relatórios e bancos podem conter dados pessoais e conteúdo de mensagens pendentes. Não os compartilhe como exemplos públicos. Antes de cada commit, confira os arquivos preparados com `git diff --cached --name-only`. O `.gitignore` não remove arquivos que já estejam rastreados.

## Testes

```bash
python -m unittest discover -s tests -v
```

Os testes publicados verificam extração MIME, HTML, seleção de frases, promoções, limites do período em Brasília, geração de e-mail multipart e controle de repetição dos relatórios diários. As chamadas de envio são simuladas nos testes.

## Estrutura

```text
gmail-digest/
├── authorize.py          # Autorização OAuth local
├── digest.py             # Leitura, extração e relatório Markdown
├── history.py            # Histórico SQLite do relatório local
├── send_digest.py        # Seleção e envio incremental por e-mail
├── daily_digest.py       # Relatório diário completo em HTML
├── demo.json             # Mensagens fictícias
├── requirements.txt      # Dependências
├── tests/                # Testes automatizados
└── .github/workflows/    # CI e agendamento do relatório local
```

## Próximas evoluções

- Configuração de filtros e remetentes por perfil.
- Histórico persistente de resumos no painel web.
- Agendamento de entregas com armazenamento persistente.
- Gestão de várias contas com isolamento dos dados de cada cliente.
- Instalação reproduzível com dependências travadas.

## Referências

- [Gmail API: início rápido com Python](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [Gmail API: envio de mensagens](https://developers.google.com/workspace/gmail/api/guides/sending)
- [OAuth 2.0: expiração de tokens](https://developers.google.com/identity/protocols/oauth2#expiration)
- [GitHub Actions: eventos e agendamento](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)

## Licença

[MIT](LICENSE). Projeto independente, sem vínculo oficial com o Google.

## Painel web

O painel consulta uma conta autorizada em modo de leitura. A cada atualização,
busca os e-mails da data escolhida, mostra resumos extraídos das mensagens e
permite pesquisar por assunto, remetente ou conteúdo. O filtro de importantes
usa as regras do projeto. Os contadores representam as mensagens carregadas.

O painel não envia e-mails e não utiliza os bancos de histórico dos comandos
anteriores. Não possui cadastro de usuários nem conexão de várias contas.
A senha protege o acesso à conta configurada no servidor.

### Iniciar no Windows

Abra um terminal na pasta que contém `web.py` e `requirements.txt`.

```powershell
python -m pip install -r requirements.txt
```

Para mensagens reais, coloque `credentials.json` nessa mesma pasta e execute:

```powershell
python authorize.py
```

Autorize sua conta no navegador. O comando cria `token.json`. Quem já possui
um token válido pode reutilizá-lo. Para usar os comandos de envio do projeto,
autorize com `python authorize.py --send-email`.

Inicie o painel com este comando, compatível com PowerShell e Git Bash:

```powershell
python -c "import os; os.environ['DASHBOARD_PASSWORD']='teste123'; os.environ['COOKIE_SECURE']='0'; from web import app; app.run(host='127.0.0.1', port=5001)"
```

Abra **http://127.0.0.1:5001** e entre com `teste123`. Essa senha é apenas um
exemplo para teste local. Deixe o terminal aberto; `Ctrl+C` encerra o servidor.
O servidor de desenvolvimento é destinado ao teste local.

### Problemas comuns

| Mensagem | Como resolver |
| --- | --- |
| `requirements.txt` ou `web.py` não encontrado | Entre na pasta que contém esses arquivos antes de executar. |
| `No module named flask` | Execute `python -m pip install -r requirements.txt` com o mesmo Python usado para iniciar. |
| `credentials.json` não encontrado | Coloque o JSON OAuth original ao lado de `authorize.py` e execute nessa pasta. |
| `Configure DASHBOARD_PASSWORD` | Pare o servidor e inicie com o comando completo acima. |
| Login retorna à tela inicial | No teste HTTP local, use `COOKIE_SECURE=0`. |
| Não foi possível consultar o Gmail | Confira a conexão e a autorização; se necessário, execute `python authorize.py` novamente. |

`credentials.json` e `token.json` são arquivos diferentes. Não renomeie um
para substituir o outro. Avisos de atualização do pip não são erros de instalação.

### Publicação

O projeto inclui `render.yaml` com configuração para hospedagem Python e
inicialização por Gunicorn. A publicação depende de configurar o serviço e
suas variáveis privadas; executar localmente ou enviar ao GitHub não publica
o painel na internet.

| Variável | Finalidade |
| --- | --- |
| `DASHBOARD_PASSWORD` | Senha longa e única para entrar no painel. |
| `SECRET_KEY` | Chave de sessão estável, compartilhada pelos processos do servidor. |
| `GMAIL_TOKEN_JSON` | Conteúdo do token autorizado, definido somente no ambiente privado da hospedagem. |
| `COOKIE_SECURE` | Use `1` em produção com HTTPS e `0` somente no teste HTTP local. |

Confira as condições e o preço da hospedagem antes de contratar.
Não envie credenciais, tokens, relatórios ou bancos ao GitHub.

### Limitações

- Até 200 mensagens por consulta; o painel avisa quando houver mais resultados.
- Resumos extrativos e regras de seleção podem deixar passar informações.
- Sem análise de anexos, cache ou atualização automática em segundo plano.
- A autorização Google pode precisar ser renovada quando revogada ou inválida.
- O painel ainda não inclui limitação de tentativas de login nem gestão de usuários;
  essas proteções precisam ser consideradas antes de disponibilizar acesso amplo.

### Arquivos do painel

```text
web.py                  # Rotas, login e consulta
static/panel.css        # Layout responsivo
templates/login.html    # Tela de entrada
templates/dashboard.html # Painel de mensagens
tests/test_web.py       # Testes com consultas simuladas
render.yaml             # Configuração de hospedagem
```
