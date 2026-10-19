# Gmail Digest 

Automação em Python para transformar mensagens do Gmail em um relatório curto, destacando trechos com possíveis prazos e ações. Projeto de portfólio com OAuth 2.0, integração REST, tratamento MIME, testes e GitHub Actions.

## O que faz

- Na primeira execução, busca as últimas 24 horas; depois retoma o histórico com cinco minutos de sobreposição.
- Salva IDs, remetentes, assuntos, datas e execuções em SQLite, evitando reprocessamento.
- Extrai texto simples ou HTML de mensagens MIME.
- Seleciona até duas frases relevantes por mensagem e agrupa promoções.
- Gera Markdown com remetente, assunto e link para o Gmail.
- Executa uma demonstração sem conta, dependências externas ou dados reais.
- Agenda execuções em repositórios privados pelo GitHub Actions.

**É um resumo extrativo por regras, não uma IA generativa.** Não entende todos os contextos nem garante identificar urgências. Anexos não são resumidos. O comando `digest.py` não envia, apaga nem marca mensagens como lidas. O envio opcional fica no comando separado `send_digest.py`.

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

O arquivo `.github/workflows/daily.yml` usa 11h17 UTC, equivalente a 08h17 em Brasília. O GitHub pode atrasar execuções: não é um serviço de horário garantido. O cursor persistente retoma a busca após falhas; mantenha o mesmo banco entre execuções.

Para usar com mensagens reais:

1. Suba uma cópia para um **repositório privado**.
2. Vá a **Settings → Secrets and variables → Actions → New repository secret**.
3. Nome: `GMAIL_TOKEN_JSON`. Valor: conteúdo completo de seu `token.json`.
4. Configure um runner próprio persistente com os labels `self-hosted` e `gmail-digest`. Crie a variável de Actions `GMAIL_HISTORY_DB` com um caminho absoluto fora do checkout, por exemplo `/srv/gmail-digest/history.sqlite3`. O workflow agora exige esse runner, pois runners hospedados descartam o banco entre execuções. Sem ele, a tarefa ficará aguardando.
5. Ative o Actions e execute **Resumo diário privado → Run workflow** para testar.
6. Baixe o arquivo `resumo-gmail` na seção **Artifacts** da execução. Ele permanece por um dia. Pessoas com acesso ao repositório poderão acessar o relatório.

O workflow diário bloqueia execução em repositórios públicos. Para o portfólio público, publique o código e a demonstração fictícia: o CI não usa credenciais. O workflow atual gera somente o arquivo; não executa o envio opcional por e-mail.

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

Possíveis evoluções: painel web, classificação melhor de newsletters, envio opcional com autorização explícita e dependências travadas com hashes. As bibliotecas estão limitadas por versão principal, mas não há lockfile reproduzível.

## Referências

- [Gmail API: quickstart Python](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [OAuth 2.0: expiração de refresh tokens](https://developers.google.com/identity/protocols/oauth2#expiration)
- [GitHub Actions: eventos e agendamento](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [GitHub Actions: secrets](https://docs.github.com/en/actions/how-tos/administering-github-actions/sharing-workflows-secrets-and-runners-with-your-organization)

Licença: MIT. Este projeto é independente do Google.

## Histórico SQLite

```bash
python digest.py --demo
python digest.py --demo
python digest.py --database data/gmail.sqlite3
```

A primeira demonstração registra 3 mensagens; a segunda registra 0. Demonstração e Gmail usam bancos separados por padrão. O relatório mostra somente mensagens novas e é substituído em cada execução. `--hours` define a janela inicial; depois o cursor governa a busca. Para consultar outro período sem afetar o histórico principal, use outro banco e outro arquivo de saída.

`messages` contém ID, remetente, assunto, data recebida (`internalDate` do Gmail em milissegundos) e data de processamento. `runs` registra início, fim, status, quantidade, corte de busca e cursor. Falhas guardam apenas o tipo de erro, sem conteúdo privado.

O cursor só avança após busca completa e gravação do relatório. Falhas ou limite atingido preservam a janela para nova tentativa; aumente `--max-messages` quando necessário. O banco serializa execuções concorrentes. Não há transação única entre arquivo e SQLite: se o processo cair após gravar o relatório e antes do commit, a próxima execução poderá gerar novamente o mesmo conteúdo.

Use **um banco por conta**, em disco persistente, e faça backup. Não compartilhe um banco entre demo e Gmail. Os arquivos SQLite e `data/` são ignorados pelo Git. Este estágio é local e para uma conta por banco; ainda não implementa isolamento de clientes de um serviço comercial ; o envio opcional está documentado abaixo.

## Enviar por e-mail (opcional)

O remetente será a conta autorizada em `token.json`. Para habilitar a permissão de envio, autorize novamente:

```bash
python authorize.py --send-email
```

Confira primeiro uma prévia (não envia e não altera o histórico):

```bash
python send_digest.py --to destinatario@example.com --preview
```

Abra `output/previa-email.txt`. Para enviar:

```bash
python send_digest.py --to destinatario@example.com
```

Para incluir um remetente prioritário, acrescente `--priority-sender cliente@example.com` (pode repetir). A seleção considera o marcador IMPORTANT do Gmail, remetentes prioritários e palavras-chave de prazo/ação no assunto ou corpo. Promoções e resumos do próprio projeto são excluídos. É uma heurística: pode ignorar mensagens relevantes ou selecionar outras sem urgência. Não resume anexos. Os links só abrem para quem tiver acesso à caixa original.

Sem mensagens novas selecionadas, nenhum e-mail é enviado. O histórico de entrega é independente do relatório local: a primeira execução de envio pode incluir mensagens já vistas com `digest.py`. O banco padrão é separado por conta de origem e destinatário e fica em `data/`. Mudanças nos filtros não reprocessam mensagens antigas; use outro banco para um novo levantamento deliberado. Não altere o banco em uso para trocar o destinatário.

A caixa de saída SQLite salva o resumo e o cursor juntos antes do envio. Um envio sem confirmação fica bloqueado, inclusive após queda do processo. Confira a pasta Enviados, o destinatário e o assunto antes de resolver:

```bash
# Se confirmou que foi enviado:
python send_digest.py --to destinatario@example.com --resolve-uncertain sent
# Somente se conferiu e deseja reenviar (pode duplicar):
python send_digest.py --to destinatario@example.com --resolve-uncertain retry
```

Os comandos de resolução também continuam a busca e o envio de novas mensagens. O envio usa a Gmail API, sem repetição automática da chamada `send`. O conteúdo pendente fica no SQLite até a confirmação; proteja esse arquivo, além dos tokens e relatórios. O comando é manual nesta versão; não foi adicionado ao agendamento diário. Exige as mesmas dependências de `requirements.txt`.

Referência: https://developers.google.com/workspace/gmail/api/guides/sending

## Resumo diário completo em HTML, sem emojis

Atualize as dependências para incluir os fusos horários no Windows:

```bash
python -m pip install -r requirements.txt
python daily_digest.py --to destinatario@example.com --preview
```

Abra `output/previa-diaria.html` no navegador. O relatório mostra assunto, remetente, horário local, resumo extrativo e link para o Gmail. O envio inclui versões HTML e texto simples.

```bash
python daily_digest.py --to destinatario@example.com
# Um dia anterior completo:
python daily_digest.py --to destinatario@example.com --date 2026-10-18
```

O comando usa o dia civil em `America/Sao_Paulo`, da meia-noite até o momento da execução (ou até a próxima meia-noite para dias passados). Ele busca todas as mensagens selecionadas da data, independentemente do histórico incremental de outros comandos. Mensagens com horário exatamente na meia-noite inicial são incluídas; o limite final é exclusivo. Se houver paginação além do limite de 500 mensagens, ele não envia um relatório incompleto; aumente `--max-messages`.

A seleção de importância continua sendo por regras; promoções são excluídas. `--priority-sender` pode ser repetido. O texto exibido é escapado e os emojis são removidos. Um dia sem mensagens selecionadas gera um relatório informando essa ausência. O comando não agenda envios futuros.

A entrega usa um banco próprio `data/diario-*.sqlite3`, vinculado à conta e ao destinatário. O mesmo conjunto de mensagens da mesma data não é reenviado. Se chegarem novas mensagens importantes, a execução seguinte envia uma versão atualizada com o dia inteiro. Falhas sem confirmação bloqueiam nova tentativa automática. Para resolver após conferir Enviados, use `--resolve-uncertain sent` ou `--resolve-uncertain retry` (este último pode duplicar). Não apague o banco para contornar o bloqueio.

O pacote `atualizacao-resumo-diario.zip` contém arquivos diretamente na raiz. Copie seu conteúdo para a pasta atual onde estão `authorize.py` e `send_digest.py`, substituindo os arquivos de código. Não contém credenciais, tokens ou bancos; preserve os seus.
