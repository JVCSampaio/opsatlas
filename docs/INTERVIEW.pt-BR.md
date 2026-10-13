# Apresentação do projeto

## Descrição curta

O OpsAtlas é uma aplicação para consultar procedimentos técnicos. O usuário cadastra documentos e faz perguntas. A resposta mostra os trechos utilizados e a revisão da fonte. A API usa Python/FastAPI e a interface usa Angular. A configuração completa inclui indexação por Kafka, PostgreSQL, auditoria MongoDB e avaliação da busca pelo Airflow.

## Demonstração de três minutos

1. Carregue os exemplos e mostre os documentos prontos.
2. Pergunte sobre o atraso dos consumidores Kafka e abra a fonte.
3. Faça uma pergunta sem resposta nos exemplos.
4. Cadastre um documento e atualize o mesmo identificador para criar uma revisão.
5. Abra Avaliação e execute os testes da busca.
6. Mostre os resultados da CI e os manifests de infraestrutura.

## Decisões técnicas

- A outbox grava o evento junto do documento. A publicação pode repetir; o consumidor ignora revisões já indexadas.
- O SQL guarda o registro original da auditoria. O MongoDB recebe uma cópia com UUID estável.
- A consulta limita os trechos enviados ao LLM e valida os IDs citados. Isso não garante a veracidade de cada frase gerada.
- O modo extrativo permite testar sem GPU ou chave. O modo LLM usa um provedor configurado.
- Para bases maiores, faltam índice de busca no banco, migrações, autenticação por tenant e tratamento de eventos com falhas repetidas.

## Texto para currículo

OpsAtlas: aplicação de consulta de procedimentos técnicos com Python/FastAPI e Angular/TypeScript. RAG com fontes, documentos versionados, indexação por Kafka, PostgreSQL, auditoria MongoDB, avaliações Airflow, observabilidade e deploy Kubernetes.

Apresente como projeto de portfólio. Consulte `VALIDATION.md` para descrever os testes executados.
