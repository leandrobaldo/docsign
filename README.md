# DocuSign → SQL → Power BI

Integração completa que extrai dados da API do DocuSign, armazena em banco SQL
e disponibiliza views prontas para consumo no Power BI.

---

## Estrutura do projeto

```
docusign_powerbi/
├── config.py            # Credenciais e configurações (NÃO versionar no Git)
├── models.py            # Tabelas SQL via SQLAlchemy ORM
├── docusign_client.py   # Autenticação JWT + wrapper da API
├── sync.py              # ETL incremental (ponto de entrada)
├── views_powerbi.sql    # Views SQL otimizadas para o Power BI
├── private.key          # Chave privada RSA (NÃO versionar no Git)
└── requirements.txt
```

---

## Pré-requisitos

### 1. Conta DocuSign — configurar o app de integração

1. Acesse **DocuSign Admin → Apps and Keys → Add App and Integration Key**
2. Em **Authentication**, escolha **JWT Grant**
3. Gere um par de chaves RSA → salve a **chave privada** como `private.key`
4. Anote: `Integration Key`, `Account ID` e `User ID`
5. Conceda consentimento abrindo **uma vez** no browser:
   ```
   https://account.docusign.com/oauth/auth
     ?response_type=code
     &scope=signature%20impersonation
     &client_id=<SEU_INTEGRATION_KEY>
     &redirect_uri=https://www.docusign.com
   ```

### 2. Preencher `config.py`

```python
DOCUSIGN = {
    "integration_key": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "account_id":      "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "user_id":         "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "private_key_path": "private.key",
    "base_url":        "https://na4.docusign.net/restapi",  # veja sua região
    "auth_server":     "account.docusign.com",
}

DATABASE = {
    # SQLite para testes:
    "connection_string": "sqlite:///docusign.db",

    # SQL Server:
    # "connection_string": "mssql+pyodbc://user:pass@servidor/banco?driver=ODBC+Driver+17+for+SQL+Server",

    # PostgreSQL:
    # "connection_string": "postgresql://user:pass@localhost/banco",
}
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

---

## Executar

```bash
# Sincronização manual
python sync.py

# Agendar execução periódica (Linux/Mac — a cada hora)
# Adicione ao crontab:  0 * * * * /usr/bin/python3 /caminho/sync.py >> sync.log 2>&1

# Windows — Task Scheduler aponta para:
# python.exe C:\caminho\sync.py
```

Na **primeira execução** são buscados os últimos 90 dias (configurável em `INITIAL_LOOKBACK_DAYS`).
Nas execuções seguintes, apenas os envelopes alterados desde a última sync são processados.

---

## Criar views no banco

Após a primeira sync, execute o arquivo SQL no seu banco:

```bash
# SQLite
sqlite3 docusign.db < views_powerbi.sql

# PostgreSQL
psql -d banco -f views_powerbi.sql

# SQL Server (SSMS ou sqlcmd)
sqlcmd -S servidor -d banco -i views_powerbi.sql
```

> ⚠️ As views usam `strftime` (SQLite). Para SQL Server use `FORMAT()`, para PostgreSQL use `TO_CHAR()`.
> As linhas comentadas no arquivo SQL mostram a sintaxe correta para cada banco.

---

## Conectar no Power BI

1. Abra o **Power BI Desktop**
2. **Obter Dados → SQL Server** (ou PostgreSQL / SQLite via ODBC)
3. Conecte no banco e importe as views:
   - `vw_envelopes` → tabela principal
   - `vw_recipients` → detalhe por signatário
   - `vw_kpis` → cartões de resumo
   - `vw_monthly_volume` → gráfico de tendência
   - `vw_sender_ranking` → ranking de remetentes
4. Configure atualização agendada no **Power BI Service**

---

## Tabelas criadas automaticamente

| Tabela | Descrição |
|---|---|
| `envelopes` | Um registro por envelope |
| `recipients` | Um registro por destinatário por envelope |
| `sync_state` | Controle de última sincronização |

---

## Segurança

- Nunca versione `config.py` ou `private.key` no Git
- Adicione ambos ao `.gitignore`
- Em produção, use variáveis de ambiente ou Azure Key Vault para as credenciais
