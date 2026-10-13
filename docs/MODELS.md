# Configuração de modelos

O modo padrão, `extractive`, mostra um trecho do documento. Não chama um LLM.

Para gerar respostas, copie `.env.example` para `.env` e configure um servidor compatível com a API OpenAI:

```dotenv
OPSATLAS_LLM_MODE=llm
OPSATLAS_LLM_BASE_URL=http://127.0.0.1:8081/v1
OPSATLAS_LLM_MODEL=identificador-do-modelo
OPSATLAS_LLM_API_KEY=
OPSATLAS_EMBEDDING_MODEL=identificador-do-modelo-de-embeddings
```

O modelo de embeddings é opcional. Reinicie a API e o worker após a mudança. Dentro do Docker, use `http://host.docker.internal:8081/v1` para acessar um servidor na máquina local.

## Contrato do provedor

O chat usa `/chat/completions` com saída JSON. São esperados os campos `answer`, `citation_ids` e `abstained`. O prompt pede uma resposta em português. Saída inválida ou fonte inexistente resulta em HTTP 502.

Os embeddings usam `/embeddings`. A aplicação verifica índices do lote, quantidade de vetores, dimensões e valores finitos. A chave do provedor deve ficar no ambiente, fora do repositório.

Sem modelo de embeddings, `lexical-hash-v1` usa características de palavras. A busca exige palavras em comum para evitar resultados causados apenas por colisões do hash.

## Reindexação

Ao trocar o modelo de embeddings, reindexe os documentos. O projeto não mistura vetores de perfis diferentes. Na demonstração, pode-se recriar a base ou enviar uma revisão com conteúdo alterado. Para uma base real, é necessário um processo de reindexação em lote.

A contagem de tokens vem do campo `usage` informado pelo provedor. O modo extrativo não gera tokens de LLM.
