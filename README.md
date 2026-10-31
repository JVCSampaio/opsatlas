# OpsAtlas

Aplicação para cadastrar procedimentos técnicos e responder perguntas com os trechos dos documentos usados na resposta.

[![CI](https://github.com/JVCSampaio/opsatlas/actions/workflows/ci.yml/badge.svg)](https://github.com/JVCSampaio/opsatlas/actions/workflows/ci.yml)

O usuário cadastra um documento em texto ou Markdown e faz uma pergunta. A aplicação busca trechos relacionados, mostra a resposta e identifica a fonte e a revisão. Se não encontrar informação, avisa que não há resposta nos documentos.

O modo padrão exibe um trecho do documento, sem usar LLM. Um provedor de chat e embeddings pode ser configurado para gerar respostas com RAG.

![Tela de consulta](docs/screenshots/knowledge-desk.png)

## Funcionalidades

- Cadastro e atualização de documentos com controle de revisão.
- Consulta com fontes e visualização dos trechos utilizados.
- Separação dos documentos por espaço (`tenant`).
- Avaliação da busca com perguntas de exemplo.
- Auditoria de operações e métricas da API.

## Tecnologias

| Componente | Uso no projeto |
| --- | --- |
| Python / FastAPI | API, indexação, busca e integração com LLM |
| Angular / TypeScript | Interface de cadastro, consulta e avaliação |
| PostgreSQL | Documentos, revisões e eventos pendentes de publicação |
| MongoDB | Cópia dos registros de auditoria |
| Kafka | Fila de eventos para indexação pelo worker |
| Airflow | Execução diária da avaliação da busca |
| Prometheus / Grafana / OpenTelemetry | Métricas, dashboard e traces |
| Docker / Kubernetes / GitHub Actions | Execução dos serviços, deploy e CI/CD |

A demonstração local usa SQLite e indexação no próprio processo. A configuração Docker usa PostgreSQL, Kafka e um worker separado.

## Executar localmente

Requisitos: Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/) e Node.js 24.

```sh
git clone https://github.com/JVCSampaio/opsatlas.git
cd opsatlas
uv sync --frozen
uv run uvicorn opsatlas.api:create_app --factory --host 127.0.0.1 --port 8000
```

Em outro terminal:

```sh
cd opsatlas/web
npm ci
npm start
```

Abra **http://127.0.0.1:4200**, clique em **Carregar exemplos** e pergunte: "Como reduzir o atraso dos consumidores Kafka?". Expanda a fonte para ler o trecho utilizado.

A documentação da API fica em **http://127.0.0.1:8000/docs**. O exemplo funciona sem chave de API, GPU ou Docker. Para usar um LLM, consulte a [configuração de modelos](docs/MODELS.md).

## Executar com Docker

```sh
docker compose up -d --build --wait
uv run python scripts/smoke.py
docker compose --profile airflow up -d airflow
```

| Serviço | Endereço |
| --- | --- |
| Interface | http://127.0.0.1:4200 |
| API | http://127.0.0.1:8000/docs |
| Grafana | http://127.0.0.1:3000 |
| Prometheus | http://127.0.0.1:9090 |
| Airflow | http://127.0.0.1:8080 |

O login de exemplo do Grafana é `admin` / `local-observability`. O Airflow gera o login nos logs: `docker compose logs airflow`. Esses acessos são apenas para desenvolvimento.

Instruções de Kubernetes e publicação de containers: [deploy](docs/DEPLOYMENT.md).

## Testes

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=opsatlas
cd web
npm run build
npx playwright install chromium
npm run test:e2e
```

A CI verifica API, interface, integração dos serviços, execução do DAG Airflow e deploy em um cluster Kubernetes kind. Os resultados e seus limites estão em [validação](docs/VALIDATION.md).

## Resultados

Medição local de 30/10/2026 (Windows 11, Python 3.13.13), no modo padrão da aplicação: busca lexical `lexical-hash-v2`, resposta extrativa, indexação no próprio processo e SQLite temporário, sem provedor de embeddings. Para reproduzir: `uv run python scripts/eval_retrieval.py`.

O arquivo `evals/retrieval.json` tem 20 perguntas escritas a partir dos três runbooks de exemplo. Em 17, a resposta está num runbook, e a fonte citada no primeiro trecho precisa ser ele. Nas outras 3, a resposta não está no acervo, e a busca precisa se abster.

| Medida | Resultado |
| --- | --- |
| Fonte certa no primeiro trecho | 17 de 17 |
| Abstenção correta | 3 de 3 |
| Casos aprovados | 20 de 20 |
| Latência (`latency_ms`) | mínima 1,42 ms, mediana 2,12 ms, máxima 14,36 ms |
| `pytest --cov=opsatlas` | 33 testes aprovados, cobertura de 89% |

A latência é o campo `latency_ms` de cada `POST /api/ask`, medido dentro do processo, sem rede.

A primeira medição deu 19 de 20. "Qual é a capital da França?" citou `runbooks/api-rollback` em vez de se abster, porque a palavra `da` não estava na lista de palavras ignoradas e aparece nesse runbook. Outras perguntas fora do acervo, como "Por que o céu é azul?", tinham o mesmo defeito. A lista passou a cobrir artigos, preposições e pronomes do português, e o perfil lexical subiu de `v1` para `v2`, porque os vetores antigos foram calculados com a lista anterior (ver [reindexação](docs/MODELS.md#reindexação)). Os testes exigem 20 de 20 e incluem seis perguntas fora do acervo que só têm palavras funcionais em comum com os runbooks.

O conjunto é pequeno e saiu dos próprios runbooks. Ele confere se a busca acha a fonte e se abstém quando deve. A qualidade num acervo grande e variado exige outra avaliação.

## Limites atuais

A busca percorre os trechos em Python e foi feita para bases pequenas. A chave da API não implementa autorização individual por tenant. A validação de citações verifica se as fontes existem; não garante a veracidade de cada frase gerada por um LLM. As credenciais da infraestrutura de exemplo não devem ser usadas em produção.

Mais detalhes: [arquitetura](docs/ARCHITECTURE.md).

## Autor e licença

[João Vitor Sampaio](https://github.com/JVCSampaio). Licença [MIT](LICENSE).
