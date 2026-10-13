# Arquitetura

## Fluxo de uma consulta

1. A interface envia a pergunta para a API.
2. A API busca trechos nos documentos do tenant informado.
3. O modo extrativo retorna o trecho mais relevante. No modo LLM, os trechos são enviados ao provedor de chat.
4. A resposta inclui as fontes e as revisões dos documentos.
5. A operação é registrada na auditoria.

O contexto do modelo é limitado a quatro trechos e 6.000 caracteres. Sem trechos relevantes, a API não chama o modelo.

## Indexação com Kafka

O documento, a revisão e o evento de indexação são gravados na mesma transação SQL. A tabela de eventos pendentes é a outbox. O worker publica o evento no Kafka e o marca como enviado após a confirmação do broker.

O consumidor indexa o documento e confirma o offset após o commit SQL. A entrega pode repetir; o consumidor ignora revisões já indexadas ou substituídas. No PostgreSQL, o bloqueio da linha impede indexações simultâneas da mesma revisão.

Ao atualizar um documento, seus trechos antigos deixam de aparecer na busca até que a nova revisão seja indexada. O SQLite é usado apenas na demonstração com um processo; ele não tem as mesmas garantias de bloqueio do PostgreSQL.

## Auditoria

O registro original fica no SQL. O worker copia os eventos para o MongoDB usando o UUID do evento como `_id`. Se a cópia repetir, o upsert não cria outro registro.

A auditoria guarda modo de resposta, fontes, latência e contagem de tokens. O texto das perguntas e das respostas não é gravado nela.

## Busca e respostas

Sem modelo de embeddings, a aplicação usa contagem de palavras com feature hashing. Isso não é um modelo semântico. Com um provedor de embeddings, usa os vetores retornados pelo modelo. A pontuação combina sobreposição de palavras e similaridade por cosseno.

O adapter de chat valida o JSON e os identificadores citados. Uma fonte inexistente causa erro HTTP 502. A existência de uma fonte não comprova que o modelo interpretou corretamente seu conteúdo.

## Observabilidade

O Prometheus recebe contadores de requisições, respostas sem informação e tokens, além de histogramas de latência. O Grafana tem um dashboard com essas métricas. Os traces da API, busca e geração são enviados ao Tempo por OpenTelemetry.

Os logs incluem identificador da requisição, rota, status e duração. Não incluem chaves de API ou conteúdo dos documentos.

## Escopo da infraestrutura

Docker Compose executa a aplicação, bancos, Kafka, observabilidade e, opcionalmente, Airflow. O overlay Kubernetes executa API, interface, worker e os serviços de dados em instâncias únicas para desenvolvimento.

A inicialização do banco usa `create_all`. Para produção, faltam migrações versionadas, autorização por usuário e tenant, limites de requisições, políticas de rede, backups e fila para eventos que falham repetidamente. A busca também precisa de um índice adequado quando a base crescer.
