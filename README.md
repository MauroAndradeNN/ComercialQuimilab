# 📊 Dashboard de Vendas & CRM - Quimilab

Este repositório contém a aplicação interativa de Business Intelligence focada em vendas, estruturada em Python utilizando o framework Streamlit. O objetivo principal do painel é segmentar a base de clientes (Varejo vs Institucional) e aplicar lógicas avançadas de CRM e Inteligência de Dados.

## ⚙️ Tratamento de Dados (Engenharia)

* **Unificação Comercial:** O sistema cria a coluna `Responsável pela Venda` priorizando o Vendedor CLT. Caso nulo, busca o Representante, garantindo 100% de rastreabilidade.
* **Normalização:** Valores financeiros convertidos do padrão brasileiro para o padrão computacional para cálculos precisos de KPIs.

## 🧠 Lógicas de CRM Aplicadas

### 1. Recência (Status de Inatividade)
Calculada comparando a última compra com a data mais recente da base.
* **🟢 Ativo:** Compras nos últimos 30 dias.
* **🟡 Risco:** Entre 31 e 60 dias sem comprar.
* **🟠 Em Evasão:** Entre 61 e 90 dias.
* **🔴 Perdido:** Mais de 90 dias (3 meses) sem registro.

### 2. Frequência de Compra
Média de Notas Fiscais únicas emitidas por cliente no período, refletindo a recorrência real de pedidos.

### 3. Abandono de Produto (Cross-Sell / Recuperação)
Identifica se um cliente que comprava o "Produto A" (há mais de 60 dias) parou de adquiri-lo nos últimos 2 meses. Gera uma lista de oportunidades de recuperação.

### 4. Positivação
Contagem de CPFs/CNPJs únicos que geraram faturamento no período filtrado.
