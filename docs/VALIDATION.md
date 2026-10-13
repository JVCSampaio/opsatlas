# Validação

A versão inicial foi testada em 13/10/2026. A [CI da revisão a97f307](https://github.com/JVCSampaio/opsatlas/actions/runs/38473866500) passou nos quatro jobs.

| Verificação | Resultado da versão inicial |
| --- | --- |
| Python | 23 testes; cobertura local de 89%; Ruff aprovado |
| Angular | Build de produção aprovado |
| Navegador | Consulta, fontes, pergunta sem resposta, avaliação e cadastro em celular |
| Docker Compose | PostgreSQL, Kafka, worker e auditoria MongoDB testados pela API |
| Observabilidade | Scrape do Prometheus e dashboard Grafana verificados |
| Airflow | Tarefas de carga e avaliação executadas; DAG terminou com sucesso |
| Kubernetes | Cluster kind, deploy dos serviços e teste de ingestão e consulta aprovados |

API e interface foram testadas em Windows e Linux. Containers, Airflow e Kubernetes rodaram nos runners Linux do GitHub Actions: a máquina Windows usada na criação estava sem virtualização disponível.

As capturas de tela são geradas pelos testes de navegador. A CI atual fica disponível em [Actions](https://github.com/JVCSampaio/opsatlas/actions).

## O que os testes não medem

A suíte de quatro perguntas verifica a seleção das fontes de exemplo e uma pergunta sem resposta. Ela não mede inteligência geral de um modelo.

Não havia servidor de LLM ativo na validação inicial. O adapter tem testes de contrato para respostas do provedor, citações, embeddings e uso de tokens. A qualidade de respostas de um modelo real não foi medida.

O conjunto de desenvolvimento emite um aviso de depreciação do adapter httpx usado pelo Starlette. Os testes passam.
