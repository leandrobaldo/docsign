# =============================================================
# config.py — Configurações da integração DocuSign + SQL
# =============================================================
# Preencha com suas credenciais antes de executar

DOCUSIGN = {
    # Encontre em: DocuSign Admin > Apps and Keys
    "integration_key": "SEU_INTEGRATION_KEY",       # Client ID do app
    "account_id":      "SEU_ACCOUNT_ID",             # Account ID (GUID)
    "user_id":         "SEU_USER_ID",                # User ID (GUID)

    # Caminho para a chave privada RSA (gerada no painel DocuSign)
    "private_key_path": "private.key",

    # URL base — produção
    "base_url": "https://na4.docusign.net/restapi",  # ajuste a região (na1, na2, eu1...)
    "auth_server": "account.docusign.com",
}

DATABASE = {
    # Exemplos de connection string:
    #   SQL Server : "mssql+pyodbc://user:pass@servidor/banco?driver=ODBC+Driver+17+for+SQL+Server"
    #   PostgreSQL : "postgresql://user:pass@localhost/banco"
    #   SQLite     : "sqlite:///docusign.db"   ← ótimo para testes locais
    "connection_string": "sqlite:///docusign.db",
}

# Quantos dias para trás buscar envelopes na primeira execução
INITIAL_LOOKBACK_DAYS = 90
