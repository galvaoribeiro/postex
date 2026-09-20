# Motor de Conteudo

SaaS de estrategia de conteudo com IA para pequenos negocios e autonomos manterem
presenca consistente no Instagram. O produto nao gera posts genericos: ele entende
o negocio (segmento, publico, diferenciais, produtos e servicos) e, a partir desse
contexto, cria o **conteudo pronto para revisao** (roteiro, legenda, CTA, hashtags,
cenas por formato) em um unico job, e um **still de capa** gerado a partir do
contexto do negocio e da peca (mock local, OpenAI ou Flux).

Fluxo do produto:

```
Usuario -> Onboarding (negocio + item + objetivo)
        -> Inicio (atalho)
        -> Criar (perguntas -> job unico -> preview)
        -> Aprovar / Agendar -> Calendario
```

A geracao de ideias continua existindo no backend, como etapa interna do job
`CONTENT_CREATION`. A tela de Ideias ficou em Configuracoes, sem ser o caminho
diario. Detalhes em [ARCHITECTURE.md](ARCHITECTURE.md).

## Stack

| Camada     | Tecnologias |
|------------|-------------|
| Frontend   | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, TanStack Query 5, react-hook-form + Zod |
| Backend    | FastAPI, Python 3.12, SQLAlchemy 2 (async/asyncpg), Pydantic v2, Alembic |
| Banco      | PostgreSQL 16 |
| Fila/Async | Redis 7 + Celery (jobs de IA em background) |
| Storage    | MinIO (S3-compatible) com URLs assinadas, S3 real em producao |
| IA         | Texto (`AIProvider`) e still (`ImageProvider`): `mock` ou `openai`, independentes |

## Estrutura do repositorio

```
POSTEX/
├── backend/           # API FastAPI
│   ├── app/
│   │   ├── api/       # routers (v1)
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # regras de negocio
│   │   ├── repositories/
│   │   ├── ai/        # AIProvider, prompts, motor de conteudo, taxonomia
│   │   ├── workers/   # Celery app e tasks
│   │   └── core/      # config, database, security, exceptions, logging
│   ├── alembic/       # migrations
│   ├── tests/         # pytest
│   └── Dockerfile
├── frontend/          # Next.js App Router
│   └── src/
│       ├── app/       # rotas (inicio, criar, contents, calendar, settings, ...)
│       ├── components/
│       └── lib/       # api client, hooks, query-keys, utils
├── docker-compose.yml # Postgres + Redis + MinIO + api + worker (uso local)
├── .env.example
└── README.md
```

## Rodando localmente

### Opcao A - Docker Compose (recomendado)

Sobe Postgres, Redis, MinIO, a API e o worker de Celery. O frontend roda fora do
compose (via `npm run dev`) para manter hot-reload rapido no Windows/macOS.

```bash
cp .env.example .env
# ajuste SECRET_KEY, AI_PROVIDER etc. se necessario

docker compose up -d --build

# primeiro acesso: crie o arquivo de env do frontend
cp frontend/.env.local.example frontend/.env.local

cd frontend
npm install
npm run dev
```

- API: http://localhost:8000 (docs interativos em `/docs`)
- Frontend: http://localhost:3000
- MinIO console: http://localhost:9001 (usuario/senha em `S3_ACCESS_KEY`/`S3_SECRET_KEY`)

> No Windows, se o Docker Desktop ficar preso ("Engine running" mas o CLI nao
> responde), reinicie o Docker Desktop antes de rodar `docker compose up`.

### Opcao B - Backend sem Docker (dev rapido)

Util para iterar no backend com reload mais rapido, mantendo Postgres/Redis/MinIO
no Docker:

```bash
docker compose up -d postgres redis minio

cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt -r requirements-dev.txt

# ajuste no .env: DATABASE_URL/REDIS_URL apontando para localhost
# (as portas publicadas estao em POSTGRES_PORT/REDIS_PORT/S3_PORT)

alembic upgrade head
uvicorn app.main:app --reload
```

Rodar o worker de Celery (necessario para geracao de ideias/conteudo com IA em
modo assincrono; use `AI_EXECUTION_MODE=inline` no `.env` para rodar sem worker):

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

## Testes

```bash
cd backend
pytest -q
```

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

## Variaveis de ambiente

Veja `.env.example` para a lista completa e comentada. Pontos importantes:

- `AI_PROVIDER=mock` permite usar o produto ponta a ponta **sem nenhuma chave de
  API**, com um provider determinístico derivado dos dados reais do negocio.
  Troque para `openai` e preencha `OPENAI_API_KEY` para usar IA real.
- `IMAGE_PROVIDER` segue `AI_PROVIDER` se vazio. Use `mock` para stills locais
  mesmo com texto real (sem gastar credito de imagem). Still real: `openai` +
  `OPENAI_IMAGE_MODEL` (padrao `gpt-image-2`) ou `flux` + `FAL_KEY` (fal.ai).
  Se o item focado tiver uma foto `READY`, o still e condicionado a esses pixels:
  OpenAI usa `images.edit`; Flux usa `FAL_KONTEXT_MODEL` (padrao
  `fal-ai/flux-pro/kontext`). Sem foto, o caminho permanece text-to-image
  (`images.generate` / `FAL_IMAGE_MODEL`).
- O visual base da capa vive em `backend/app/ai/image/prompt.py` (`CREATIVE_BRIEF`).
  Produto, marca, local e cena da peca entram automaticamente no prompt; nao ha
  seletor de tom ou apresentadora na UI. O produto e a foto dele sao escolhidos
  em `/criar`; Configuracoes → Produtos so edita o que ja existe.
- `AI_EXECUTION_MODE`: `celery` (producao, exige worker) ou `inline` (executa no
  processo da API, util para dev/testes sem worker).
- Nenhuma chave de IA e exposta ao frontend; todas as chamadas de IA passam pelo
  backend.

## Deploy (Railway)

O projeto foi desenhado para ser 12-factor e compativel com Railway sem mudancas
estruturais:

- Configuracao 100% via variaveis de ambiente (`DATABASE_URL`, `REDIS_URL`,
  `SECRET_KEY`, etc.), sem caminhos absolutos ou dependencias do Windows.
- O `Dockerfile` do backend serve tanto o servico `api` quanto o `worker`
  (mesma imagem, comando diferente via `docker-entrypoint.py api|worker`),
  o que mapeia direto para dois servicos Railway a partir do mesmo repo.
- `docker-compose.yml` e usado **apenas para desenvolvimento local**; em
  producao, Postgres/Redis/Storage serao servicos gerenciados (Railway
  Postgres/Redis + um S3-compatible, ex.: Railway Volumes + MinIO ou um bucket
  S3 real) referenciados por variaveis de ambiente injetadas pela plataforma.
- Migrations rodam automaticamente no boot do servico `api`
  (`alembic upgrade head`), sem passo manual.

Passos gerais quando for migrar para Railway: criar servicos para `api`,
`worker`, Postgres e Redis a partir do mesmo repo/Dockerfile, configurar as
variaveis de ambiente equivalentes ao `.env.example`, apontar um bucket
S3-compatible para `S3_*`, e configurar `CORS_ORIGINS`/`COOKIE_DOMAIN` para o
dominio publico do frontend.

## Estado atual

Fluxo funcional de ponta a ponta: registro -> onboarding em 3 passos -> Inicio
(chips de produto/objetivo) -> Criar (perguntas, job unico com stages visiveis,
preview em formato de celular) -> Aprovar / Refazer / Agendar -> biblioteca em
abas -> calendario (semana padrao). Ideias, imagens e o CRUD de catalogo
continuam em Configuracoes. Preparado para features futuras (publicacao
automatica, conexao com Instagram, metricas, planos pagos) sem necessidade de
refatoracao estrutural.
