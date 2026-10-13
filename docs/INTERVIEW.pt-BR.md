# Apresentação do projeto

## Pitch de 40 segundos

“Criei o OpsAtlas, uma central de conhecimento para operações. O usuário cadastra runbooks, faz perguntas e recebe a resposta junto da fonte e da revisão. A aplicação usa Python/FastAPI e Angular. Na configuração completa, PostgreSQL registra documentos e uma outbox transacional; Kafka entrega a ingestão para um worker idempotente; MongoDB recebe a auditoria. Airflow executa uma verificação diária de retrieval. Incluí métricas, traces, containers, testes de navegador e um deploy Kubernetes reproduzível.”

## Demonstração de três minutos

1. Carregue os exemplos e mostre os documentos prontos.
2. Pergunte sobre Kafka consumer lag e abra a citação com revisão.
3. Faça uma pergunta sem evidência e mostre a recusa.
4. Cadastre um runbook e atualize a mesma origem: a revisão aumenta.
5. Execute Quality checks e explique que a suíte mede retrieval, não inteligência geral.
6. Abra a CI e os arquivos de infraestrutura; mostre quais execuções foram comprovadas.

## Decisões que vale explicar

- **Por que outbox?** Evita salvar no banco e perder o evento na publicação. A entrega pode repetir; a idempotência está no consumidor.
- **Por que SQL e Mongo?** SQL é a autoridade transacional; Mongo é uma projeção de auditoria, com UUID estável.
- **Como reduz alucinação?** Retrieval limitado, recusa sem evidência e validação dos IDs citados. Isso não prova automaticamente a verdade de cada frase.
- **Por que dois modos?** A pessoa consegue testar sem GPU/chaves. O adapter conecta um LLM e embeddings reais quando configurados.
- **O que muda em escala?** Ranking no banco/índice vetorial, migrações, autenticação por tenant, DLQ, métricas de lag e serviços de infraestrutura gerenciados.

## Texto para currículo

“OpsAtlas — aplicação de conhecimento operacional com Python/FastAPI e Angular/TypeScript; RAG com citações e controle de revisões, ingestão Kafka via outbox transacional, PostgreSQL, auditoria MongoDB, DAG de avaliação Airflow, observabilidade Prometheus/OpenTelemetry e infraestrutura Kubernetes.”

Apresente como projeto de portfólio. O código e os testes demonstram prática; não equivalem a anos de operação dessas tecnologias em produção. Use os resultados atuais de `VALIDATION.md` ao mencionar execução de infraestrutura.
