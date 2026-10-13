# Deploy

## Docker Compose

```sh
docker compose up -d --build --wait --wait-timeout 300
uv run python scripts/smoke.py
docker compose --profile airflow up -d airflow
docker compose logs airflow
```

Os serviços publicados ficam em localhost. Banco, Kafka, MongoDB e Tempo são acessíveis pela rede interna do Compose.

As variáveis `POSTGRES_PASSWORD`, `GRAFANA_PASSWORD` e `OPSATLAS_API_KEY` podem ser definidas no `.env`. A senha de exemplo do PostgreSQL precisa ser compatível com uma URL; outra senha exige codificação na string de conexão. Alterar a variável não muda a senha de um banco já inicializado.

Para parar os serviços e manter os dados:

```sh
docker compose --profile airflow down
```

Os volumes mantêm documentos, eventos e auditoria. A opção `-v` remove esses dados.

## Kubernetes local

Requisitos: Docker Linux funcionando, kind e kubectl. Os manifests são de desenvolvimento, com credenciais de exemplo e uma instância de cada serviço de dados.

```sh
docker build -t opsatlas-api:local .
docker build -t opsatlas-web:local web
kind create cluster --name opsatlas
kind load docker-image opsatlas-api:local opsatlas-web:local --name opsatlas
kubectl apply -k infra/k8s
kubectl -n opsatlas rollout status statefulset/kafka --timeout=300s
kubectl -n opsatlas rollout status deployment/api --timeout=300s
kubectl -n opsatlas rollout status deployment/worker --timeout=300s
kubectl -n opsatlas rollout status deployment/web --timeout=300s
kubectl -n opsatlas port-forward service/web 4200:80
```

Para testar a API, abra outro terminal:

```sh
kubectl -n opsatlas port-forward service/api 8000:8000
```

Em um terceiro terminal, execute `uv run python scripts/smoke.py`.

Airflow e observabilidade estão no exemplo Compose. O overlay Kubernetes inclui a aplicação e os serviços de dados.

## CI/CD

Pushes e pull requests executam testes Python, build Angular, testes de navegador e integração dos containers. Um job também cria um cluster kind e testa a aplicação nele.

Tags `v*`, releases publicadas e execução manual do workflow de publicação geram imagens API e web no GHCR. O deploy em um cluster é feito separadamente.

Antes de expor a aplicação, substitua as credenciais de exemplo, configure autenticação por usuário e tenant, TLS, limites de requisições, migrações e backups. A probe de readiness verifica o SQL; não verifica todos os serviços externos.
