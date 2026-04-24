-- =============================================================
-- views_powerbi.sql — Views otimizadas para o Power BI
-- Execute uma vez no seu banco após a primeira sincronização
-- =============================================================


-- ── 1. Visão geral de envelopes ───────────────────────────────────────────────
-- Use como tabela principal nos seus dashboards

CREATE OR REPLACE VIEW vw_envelopes AS
SELECT
    envelope_id,
    subject,
    status,
    sender_name,
    sender_email,
    created_at,
    sent_at,
    delivered_at,
    completed_at,
    voided_at,
    void_reason,
    hours_to_sign,

    -- Flags booleanas úteis para filtros no Power BI
    CASE WHEN status = 'completed' THEN 1 ELSE 0 END  AS is_completed,
    CASE WHEN status = 'voided'    THEN 1 ELSE 0 END  AS is_voided,
    CASE WHEN status = 'declined'  THEN 1 ELSE 0 END  AS is_declined,
    CASE WHEN status IN ('sent','delivered') THEN 1 ELSE 0 END AS is_pending,

    -- Período (facilita agrupamento por mês/trimestre)
    strftime('%Y-%m', created_at)        AS year_month,   -- SQLite
    -- FORMAT(created_at, 'yyyy-MM')     AS year_month,   -- SQL Server
    -- TO_CHAR(created_at, 'YYYY-MM')    AS year_month,   -- PostgreSQL

    synced_at
FROM envelopes;


-- ── 2. Desempenho por destinatário ────────────────────────────────────────────

CREATE OR REPLACE VIEW vw_recipients AS
SELECT
    r.envelope_id,
    r.name           AS recipient_name,
    r.email          AS recipient_email,
    r.role_name,
    r.status         AS recipient_status,
    r.routing_order,
    r.sent_at,
    r.delivered_at,
    r.signed_at,
    r.declined_at,
    r.decline_reason,
    r.hours_to_sign,
    e.subject,
    e.sender_name,
    e.status         AS envelope_status,
    e.created_at     AS envelope_created_at
FROM recipients r
JOIN envelopes  e ON e.envelope_id = r.envelope_id;


-- ── 3. KPIs de alto nível (cartões do Power BI) ───────────────────────────────

CREATE OR REPLACE VIEW vw_kpis AS
SELECT
    COUNT(*)                                          AS total_envelopes,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS total_completed,
    SUM(CASE WHEN status = 'voided'    THEN 1 ELSE 0 END) AS total_voided,
    SUM(CASE WHEN status = 'declined'  THEN 1 ELSE 0 END) AS total_declined,
    SUM(CASE WHEN status IN ('sent','delivered') THEN 1 ELSE 0 END) AS total_pending,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 1
    )                                                 AS completion_rate_pct,
    ROUND(AVG(hours_to_sign), 1)                      AS avg_hours_to_sign
FROM envelopes;


-- ── 4. Volume mensal (gráfico de linha/barras) ────────────────────────────────

CREATE OR REPLACE VIEW vw_monthly_volume AS
SELECT
    strftime('%Y-%m', created_at)  AS year_month,     -- SQLite
    -- FORMAT(created_at, 'yyyy-MM') AS year_month,   -- SQL Server
    COUNT(*)                       AS total_sent,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS total_completed,
    ROUND(AVG(hours_to_sign), 1)   AS avg_hours_to_sign
FROM envelopes
GROUP BY strftime('%Y-%m', created_at)
ORDER BY year_month;


-- ── 5. Ranking de remetentes (quem mais envia) ────────────────────────────────

CREATE OR REPLACE VIEW vw_sender_ranking AS
SELECT
    sender_name,
    sender_email,
    COUNT(*)                       AS total_sent,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS total_completed,
    ROUND(AVG(hours_to_sign), 1)   AS avg_hours_to_sign
FROM envelopes
GROUP BY sender_name, sender_email
ORDER BY total_sent DESC;
