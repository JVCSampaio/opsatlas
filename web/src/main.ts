import { Component, OnDestroy, OnInit, signal } from "@angular/core";
import { bootstrapApplication } from "@angular/platform-browser";

interface Doc {
  id: string;
  title: string;
  source: string;
  status: string;
  revision: number;
}
interface Source {
  id: string;
  title: string;
  source: string;
  revision: number;
  text: string;
  score: number;
}
interface Answer {
  answer: string;
  citations: Source[];
  abstained: boolean;
  mode: string;
  latency_ms: number;
  usage: { prompt_tokens?: number; completion_tokens?: number };
}
interface Overview {
  documents: number;
  chunks: number;
  events: number;
  llm_mode: string;
  embedding_mode: string;
  ingestion_mode: string;
  activity: { kind: string; created_at: string }[];
}
interface Evaluation {
  passed: number;
  total: number;
  cases: { question: string; passed: boolean }[];
}

@Component({
  selector: "app-root",
  standalone: true,
  template: `<div class="shell">
    <aside>
      <a class="brand" href="/" aria-label="Início do OpsAtlas"
        ><span class="brand-icon">◈</span> OpsAtlas</a
      >
      <div class="workspace">DOCUMENTOS <span>01</span></div>
      <button
        class="nav"
        [class.active]="tab() === 'ask'"
        (click)="tab.set('ask')"
      >
        <span>⌘</span> Consulta
      </button>
      <button
        class="nav"
        [class.active]="tab() === 'library'"
        (click)="tab.set('library')"
      >
        <span>▤</span> Documentos <small>{{ docs().length }}</small>
      </button>
      <button
        class="nav"
        [class.active]="tab() === 'quality'"
        (click)="tab.set('quality')"
      >
        <span>◎</span> Avaliação
      </button>
      <div class="sidebar-bottom">
        <p>John Sampaio<br />Python · Angular · RAG</p>
        <a
          href="https://github.com/JVCSampaio/opsatlas"
          target="_blank"
          rel="noopener"
          >Código no GitHub ↗</a
        >
      </div>
    </aside>
    <main>
      <header>
        <span
          >OPSATLAS /
          {{
            tab() === "ask"
              ? "CONSULTA"
              : tab() === "library"
                ? "DOCUMENTOS"
                : "AVALIAÇÃO"
          }}</span
        >
        <div>
          <span class="status"
            ><i class="dot"></i
            >{{ overview() ? "API conectada" : "Conectando" }}</span
          >
          <button class="subtle" (click)="showSettings.set(!showSettings())">
            Conexão ⚙
          </button>
        </div>
      </header>
      @if (showSettings()) {
        <section class="settings">
          <label
            >Chave da API<input
              type="password"
              [value]="apiKey"
              (input)="apiKey = value($event)"
              placeholder="Opcional na demonstração local"
          /></label>
          <label
            >Espaço de documentos (tenant)<input
              [value]="tenant"
              (input)="tenant = value($event)"
          /></label>
          <button (click)="refresh(); showSettings.set(false)">Conectar</button>
          <p>A chave não é salva no navegador.</p>
        </section>
      }
      @if (error()) {
        <div role="alert" class="error">{{ error() }}</div>
      }
      <div class="page-heading">
        <div>
          <h1>
            {{
              tab() === "ask"
                ? "Consultar documentos"
                : tab() === "library"
                  ? "Cadastrar documentos"
                  : "Avaliar a busca"
            }}
          </h1>
          <p>
            {{
              tab() === "ask"
                ? "Faça uma pergunta sobre os procedimentos cadastrados e consulte os trechos usados na resposta."
                : tab() === "library"
                  ? "Adicione procedimentos em texto ou Markdown. Reutilize o identificador para atualizar um documento."
                  : "Verifique se a busca encontra os documentos esperados e identifica perguntas sem informação disponível."
            }}
          </p>
        </div>
        <button class="seed" [disabled]="busy()" (click)="seed()">
          Carregar exemplos <span>↗</span>
        </button>
      </div>
      <section class="stats" aria-label="Resumo dos documentos">
        <div>
          <span>DOCUMENTOS</span
          ><strong>{{ overview()?.documents ?? "—" }}</strong
          ><small>Procedimentos cadastrados</small>
        </div>
        <div>
          <span>TRECHOS INDEXADOS</span
          ><strong>{{ overview()?.chunks ?? "—" }}</strong
          ><small>Espaço: {{ tenant }}</small>
        </div>
        <div>
          <span>EVENTOS</span><strong>{{ overview()?.events ?? "—" }}</strong
          ><small>Registros de auditoria</small>
        </div>
        <div>
          <span>MODO DE RESPOSTA</span
          ><strong class="engine">{{
            overview()?.llm_mode === "llm" ? "LLM" : "Extrativo"
          }}</strong
          ><small>{{
            overview()?.llm_mode === "llm"
              ? "Modelo configurado na API"
              : "Exibe um trecho do documento, sem LLM"
          }}</small>
        </div>
      </section>
      @if (tab() === "ask") {
        <div class="desk">
          <section class="question-panel">
            <div class="panel-heading"><h2>Pergunta</h2></div>
            <label class="sr-only" for="question">Pergunta</label>
            <textarea
              id="question"
              [value]="question"
              (input)="question = value($event)"
              placeholder="Como reduzir o atraso dos consumidores Kafka?"
            ></textarea>
            <div class="suggestions">
              @for (prompt of prompts; track prompt) {
                <button (click)="question = prompt">{{ prompt }} ↗</button>
              }
            </div>
            <div class="question-footer">
              <span>A busca usa os documentos deste espaço.</span
              ><button
                class="primary"
                [disabled]="busy() || question.trim().length < 3"
                (click)="ask()"
              >
                {{ busy() ? "Buscando..." : "Buscar resposta" }} <span>→</span>
              </button>
            </div>
            @if (result(); as r) {
              <article class="answer" aria-live="polite">
                <div class="panel-heading">
                  <h2>
                    {{
                      r.abstained ? "Sem informação nos documentos" : "Resposta"
                    }}
                  </h2>
                  <span>{{ r.latency_ms }} ms</span>
                </div>
                <p class="answer-text">{{ r.answer }}</p>
                <div class="answer-meta">
                  {{ modeLabel(r.mode) }} · {{ r.citations.length }} fonte(s) ·
                  {{ r.usage.completion_tokens ?? 0 }} tokens gerados
                </div>
                @for (s of r.citations; track s.id) {
                  <details class="citation">
                    <summary>
                      {{ s.title }} <span>revisão {{ s.revision }} ↗</span>
                    </summary>
                    <small>{{ s.source }}</small>
                    <p>{{ s.text }}</p>
                  </details>
                }
              </article>
            } @else {
              <div class="empty-answer">
                <h3>Nenhuma consulta realizada</h3>
                <p>
                  Carregue os exemplos ou cadastre um documento.<br />Depois,
                  digite uma pergunta e clique em Buscar resposta.
                </p>
              </div>
            }
          </section>
          <section class="right-column">
            <div class="panel-heading">
              <h2>Documentos cadastrados</h2>
              <button class="text-button" (click)="tab.set('library')">
                Ver todos ↗
              </button>
            </div>
            @for (d of docs(); track d.id) {
              <div class="mini-doc">
                <span class="doc-icon">▤</span>
                <div>
                  <h3>{{ d.title }}</h3>
                  <small
                    >{{ statusLabel(d.status) }} · revisão
                    {{ d.revision }}</small
                  >
                </div>
              </div>
            }
            @if (!docs().length) {
              <p class="muted">Nenhum documento cadastrado.</p>
            }
            <div class="principle">
              <h3>Como funciona</h3>
              <p>
                A aplicação busca trechos relacionados à pergunta e mostra as
                fontes. No modo extrativo, a resposta é um trecho do documento.
                Com LLM configurado, o modelo recebe esses trechos para
                responder.
              </p>
            </div>
            <div class="activity">
              <h2>Atividade recente</h2>
              @for (
                a of overview()?.activity?.slice(0, 5) ?? [];
                track $index
              ) {
                <p>
                  <i class="dot"></i>{{ activityLabel(a.kind)
                  }}<small>{{ a.created_at.slice(11, 19) }}</small>
                </p>
              }
            </div>
          </section>
        </div>
      }
      @if (tab() === "library") {
        <section class="library-grid">
          <div class="card">
            <h2>Adicionar ou atualizar documento</h2>
            <label
              >Identificador<input
                [value]="source"
                (input)="source = value($event)"
                placeholder="procedimentos/timeout-pagamento"
            /></label>
            <label
              >Título<input [value]="title" (input)="title = value($event)"
            /></label>
            <label
              >Conteúdo<textarea
                [value]="content"
                (input)="content = value($event)"
                rows="9"
              ></textarea>
            </label>
            <button
              class="primary"
              [disabled]="busy() || !source || !title || !content"
              (click)="upload()"
            >
              Salvar documento →
            </button>
          </div>
          <div class="card">
            <h2>Documentos cadastrados</h2>
            @for (d of docs(); track d.id) {
              <div class="inventory-row">
                <h3>{{ d.title }}</h3>
                <code>{{ d.source }}</code>
                <p>
                  <span class="badge">{{ statusLabel(d.status) }}</span> revisão
                  {{ d.revision }}
                </p>
              </div>
            }
            @if (!docs().length) {
              <p>Nenhum documento cadastrado.</p>
            }
          </div>
        </section>
      }
      @if (tab() === "quality") {
        <section class="card quality">
          <div class="panel-heading">
            <h2>Testes com os exemplos</h2>
            <button class="primary" [disabled]="busy()" (click)="evaluate()">
              Executar avaliação →
            </button>
          </div>
          <p>
            A avaliação contém três perguntas com documento esperado e uma sem
            resposta nos exemplos. Ela verifica a busca, não a qualidade geral
            de um LLM.
          </p>
          @if (evaluation(); as e) {
            <h3 class="evaluation-score">
              {{ e.passed }} / {{ e.total }} testes passaram
            </h3>
            @for (c of e.cases; track c.question) {
              <div class="check">
                <span>{{ c.passed ? "✓" : "×" }}</span
                >{{ c.question
                }}<strong>{{ c.passed ? "PASSOU" : "FALHOU" }}</strong>
              </div>
            }
          }
          <div class="quality-note">
            Na configuração completa, o Airflow executa esta avaliação
            diariamente. As métricas da API ficam disponíveis no Prometheus e no
            Grafana.
          </div>
        </section>
      }
      <footer>
        <span>OpsAtlas · Consulta de procedimentos técnicos</span
        ><span>Projeto de portfólio de John Sampaio</span>
      </footer>
    </main>
  </div>`,
})
class App implements OnInit, OnDestroy {
  private poll?: ReturnType<typeof setInterval>;
  tab = signal("ask");
  busy = signal(false);
  error = signal("");
  showSettings = signal(false);
  docs = signal<Doc[]>([]);
  overview = signal<Overview | null>(null);
  result = signal<Answer | null>(null);
  evaluation = signal<Evaluation | null>(null);
  apiKey = "";
  tenant = "demo";
  question = "";
  source = "";
  title = "";
  content = "";
  prompts = [
    "Atraso dos consumidores Kafka",
    "Rollback de uma implantação",
    "Fontes de respostas RAG",
  ];
  modeLabel(mode: string): string {
    return mode === "extractive" ? "Extrativo" : "LLM";
  }
  statusLabel(status: string): string {
    return (
      ({ ready: "Indexado", queued: "Na fila" } as Record<string, string>)[
        status
      ] ?? status
    );
  }
  activityLabel(kind: string): string {
    return (
      (
        {
          "document.submitted": "Documento salvo",
          "answer.created": "Consulta realizada",
          "evaluation.completed": "Avaliação executada",
        } as Record<string, string>
      )[kind] ?? kind
    );
  }
  value(event: Event): string {
    return (event.target as HTMLInputElement).value;
  }
  ngOnInit(): void {
    void this.refresh();
    this.poll = setInterval(() => {
      if (!this.busy() && this.docs().some((doc) => doc.status === "queued")) {
        void this.refresh();
      }
    }, 2500);
  }
  ngOnDestroy(): void {
    clearInterval(this.poll);
  }
  async api<T>(path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Tenant": this.tenant,
    };
    if (this.apiKey) headers["Authorization"] = "Bearer " + this.apiKey;
    const response = await fetch("/api/" + path, {
      method: body === undefined ? "GET" : "POST",
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "Falha na requisição (" + response.status + ")",
      );
    }
    return response.json() as Promise<T>;
  }
  async refresh(): Promise<void> {
    try {
      const [docs, overview] = await Promise.all([
        this.api<Doc[]>("documents"),
        this.api<Overview>("overview"),
      ]);
      this.docs.set(docs);
      this.overview.set(overview);
      this.error.set("");
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : String(e));
    }
  }
  async action(work: () => Promise<void>): Promise<void> {
    this.busy.set(true);
    this.error.set("");
    try {
      await work();
      await this.refresh();
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.busy.set(false);
    }
  }
  seed(): void {
    void this.action(async () => {
      await this.api("demo/seed", {});
    });
  }
  ask(): void {
    void this.action(async () => {
      this.result.set(
        await this.api<Answer>("ask", { question: this.question }),
      );
    });
  }
  upload(): void {
    void this.action(async () => {
      await this.api("documents", {
        source: this.source,
        title: this.title,
        content: this.content,
      });
      this.content = "";
    });
  }
  evaluate(): void {
    void this.action(async () => {
      this.evaluation.set(await this.api<Evaluation>("evaluations", {}));
    });
  }
}
bootstrapApplication(App).catch(console.error);
