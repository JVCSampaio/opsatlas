import { Component, OnInit, signal } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';

interface Doc { id: string; title: string; source: string; status: string; revision: number; }
interface Source { id: string; title: string; source: string; revision: number; text: string; score: number; }
interface Answer { answer: string; citations: Source[]; abstained: boolean; mode: string; latency_ms: number; usage: { prompt_tokens?: number; completion_tokens?: number }; }
interface Overview { documents: number; chunks: number; events: number; llm_mode: string; embedding_mode: string; ingestion_mode: string; activity: {kind: string; created_at: string}[]; }
interface Evaluation { passed: number; total: number; cases: {question: string; passed: boolean}[]; }

@Component({
  selector: 'app-root', standalone: true,
  template: `
  <div class="shell">
    <aside>
      <a class="brand" href="/" aria-label="OpsAtlas home"><span class="brand-icon">◈</span> OpsAtlas</a>
      <div class="workspace">WORKSPACE <span>01</span></div>
      <button class="nav" [class.active]="tab() === 'ask'" (click)="tab.set('ask')"><span>⌘</span> Knowledge desk</button>
      <button class="nav" [class.active]="tab() === 'library'" (click)="tab.set('library')"><span>▤</span> Runbook library <small>{{docs().length}}</small></button>
      <button class="nav" [class.active]="tab() === 'quality'" (click)="tab.set('quality')"><span>◎</span> Quality checks</button>
      <div class="sidebar-bottom"><span class="dot"></span> Evidence before action<p>Built by John Sampaio<br>Python · Angular · RAG</p><a href="https://github.com/JVCSampaio/opsatlas" target="_blank" rel="noopener">Source code ↗</a></div>
    </aside>
    <main>
      <header><span>OPERATIONS / {{tab() === 'ask' ? 'KNOWLEDGE DESK' : tab() === 'library' ? 'LIBRARY' : 'QUALITY'}}</span><div><span class="status"><i class="dot"></i>{{overview() ? 'API connected' : 'Connecting'}}</span><button class="subtle" (click)="showSettings.set(!showSettings())">Connection ⚙</button></div></header>
      @if (showSettings()) {<section class="settings"><label>Deployment API key<input type="password" [value]="apiKey" (input)="apiKey = value($event)" placeholder="Empty for local demo"></label><label>Tenant<input [value]="tenant" (input)="tenant = value($event)"></label><button (click)="refresh(); showSettings.set(false)">Connect</button><p>The key stays in memory and is never saved in the browser.</p></section>}
      @if (error()) {<div role="alert" class="error">{{error()}}</div>}
      <div class="page-heading"><div><div class="eyebrow">YOUR OPERATIONS, WITH CONTEXT</div><h1>{{tab() === 'ask' ? 'Find the answer.\nKnow the source.' : tab() === 'library' ? 'A shared operating memory.' : 'Trust is measurable.'}}</h1><p>{{tab() === 'ask' ? 'Turn runbooks into grounded answers you can inspect.' : tab() === 'library' ? 'Versioned documents, searchable evidence and a visible ingestion state.' : 'Check retrieval and abstention before trusting the next answer.'}}</p></div><button class="seed" [disabled]="busy()" (click)="seed()">Load sample runbooks <span>↗</span></button></div>
      <section class="stats" aria-label="Workspace statistics"><div><span>INDEXED DOCUMENTS</span><strong>{{overview()?.documents ?? '—'}}</strong><small>Versioned source library</small></div><div><span>RETRIEVABLE CHUNKS</span><strong>{{overview()?.chunks ?? '—'}}</strong><small>Scoped to {{tenant}}</small></div><div><span>AUDIT EVENTS</span><strong>{{overview()?.events ?? '—'}}</strong><small>Persistent evidence trail</small></div><div><span>ANSWER ENGINE</span><strong class="engine">{{overview()?.llm_mode === 'llm' ? 'LLM' : 'Extractive'}}</strong><small>{{overview()?.llm_mode === 'llm' ? 'OpenAI-compatible provider' : 'Offline demo · no model required'}}</small></div></section>
      @if (tab() === 'ask') {
      <div class="desk"><section class="question-panel"><div class="panel-heading"><h2>Ask your runbooks</h2><span>01 / RETRIEVE</span></div><p class="muted">A precise question makes evidence easier to find.</p><label class="sr-only" for="question">Question</label><textarea id="question" [value]="question" (input)="question = value($event)" placeholder="How should I handle Kafka consumer lag?"></textarea><div class="suggestions">@for (prompt of prompts; track prompt) {<button (click)="question = prompt">{{prompt}} ↗</button>}</div><div class="question-footer"><span>⌁ Answers stay within your sources</span><button class="primary" [disabled]="busy() || question.trim().length < 3" (click)="ask()">{{busy() ? 'Searching…' : 'Find evidence'}} <span>→</span></button></div>
      @if (result(); as r) {<article class="answer" aria-live="polite"><div class="panel-heading"><h2>{{r.abstained ? 'More evidence needed' : 'Evidence-backed answer'}}</h2><span>{{r.latency_ms}} ms</span></div><p class="answer-text">{{r.answer}}</p><div class="answer-meta">{{r.mode}} · {{r.citations.length}} source(s) · {{r.usage.completion_tokens ?? 0}} generated tokens</div>@for (s of r.citations; track s.id) {<details class="citation"><summary>{{s.title}} <span>revision {{s.revision}} ↗</span></summary><small>{{s.source}}</small><p>{{s.text}}</p></details>}</article>}
      @else {<div class="empty-answer"><span>◈</span><h3>Every answer starts with evidence.</h3><p>Load the sample library, then ask a question.<br>Source excerpts will appear alongside your answer.</p></div>}
      </section><section class="right-column"><div class="panel-heading"><h2>In the library</h2><button class="text-button" (click)="tab.set('library')">View all ↗</button></div>@for (d of docs(); track d.id) {<div class="mini-doc"><span class="doc-icon">▤</span><div><h3>{{d.title}}</h3><small>{{d.status}} · revision {{d.revision}}</small></div></div>}@if (!docs().length) {<p class="muted">No documents yet. Add a runbook or load the samples.</p>}<div class="principle"><span>DESIGNED FOR ACCOUNTABILITY</span><h3>Useful answers.<br>Visible boundaries.</h3><p>No matching evidence? The assistant abstains. Every returned source carries its document revision.</p><div>SQL outbox → Kafka → Indexer</div></div><div class="activity"><h2>Recent activity</h2>@for (a of overview()?.activity?.slice(0, 5) ?? []; track $index) {<p><i class="dot"></i>{{a.kind}}<small>{{a.created_at.slice(11, 19)}}</small></p>}</div></section></div>
      }
      @if (tab() === 'library') {<section class="library-grid"><div class="card"><h2>Add or update a runbook</h2><p class="muted">Reuse the same source to create a new revision. Markdown and plain text are supported.</p><label>Source ID<input [value]="source" (input)="source = value($event)" placeholder="runbooks/payment-timeout"></label><label>Title<input [value]="title" (input)="title = value($event)"></label><label>Runbook content<textarea [value]="content" (input)="content = value($event)" rows="9"></textarea></label><button class="primary" [disabled]="busy() || !source || !title || !content" (click)="upload()">Index runbook →</button></div><div class="card"><h2>Document inventory</h2>@for (d of docs(); track d.id) {<div class="inventory-row"><h3>{{d.title}}</h3><code>{{d.source}}</code><p><span class="badge">{{d.status}}</span> revision {{d.revision}}</p></div>}@if (!docs().length) {<p>No documents yet.</p>}</div></section>}
      @if (tab() === 'quality') {<section class="card quality"><div class="panel-heading"><h2>Retrieval smoke suite</h2><button class="primary" [disabled]="busy()" (click)="evaluate()">Run evaluation →</button></div><p>Three source-selection checks and one no-evidence check against the sample runbooks. This is a transparent demo suite, not an unseen model benchmark.</p>@if (evaluation(); as e) {<h3 class="evaluation-score">{{e.passed}} / {{e.total}} checks passed</h3>@for (c of e.cases; track c.question) {<div class="check"><span>{{c.passed ? '✓' : '×'}}</span>{{c.question}}<strong>{{c.passed ? 'PASS' : 'FAIL'}}</strong></div>}}<div class="quality-note">Daily runs are orchestrated by the Airflow DAG. Prometheus records API latency, abstentions and provider-reported token usage.</div></section>}
      <footer><span>OpsAtlas / Operational knowledge platform</span><span>Sources you can inspect. Decisions you can explain.</span></footer>
    </main>
  </div>`
})
class App implements OnInit {
  tab = signal('ask'); busy = signal(false); error = signal(''); showSettings = signal(false);
  docs = signal<Doc[]>([]); overview = signal<Overview | null>(null);
  result = signal<Answer | null>(null); evaluation = signal<Evaluation | null>(null);
  apiKey = ''; tenant = 'demo'; question = ''; source = ''; title = ''; content = '';
  prompts = ['Kafka consumer lag', 'API deployment rollback', 'RAG evidence and abstention'];
  value(event: Event): string { return (event.target as HTMLInputElement).value; }
  ngOnInit(): void { void this.refresh(); }
  async api<T>(path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json', 'X-Tenant': this.tenant };
    if (this.apiKey) headers['Authorization'] = 'Bearer ' + this.apiKey;
    const response = await fetch('/api/' + path, { method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body) });
    if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed (' + response.status + ')'); }
    return response.json() as Promise<T>;
  }
  async refresh(): Promise<void> { try { const [docs, overview] = await Promise.all([this.api<Doc[]>('documents'), this.api<Overview>('overview')]); this.docs.set(docs); this.overview.set(overview); this.error.set(''); } catch (e) { this.error.set(String(e)); } }
  async action(work: () => Promise<void>): Promise<void> { this.busy.set(true); this.error.set(''); try { await work(); await this.refresh(); } catch (e) { this.error.set(String(e)); } finally { this.busy.set(false); } }
  seed(): void { void this.action(async () => { await this.api('demo/seed', {}); }); }
  ask(): void { void this.action(async () => { this.result.set(await this.api<Answer>('ask', { question: this.question })); }); }
  upload(): void { void this.action(async () => { await this.api('documents', { source: this.source, title: this.title, content: this.content }); this.content = ''; }); }
  evaluate(): void { void this.action(async () => { this.evaluation.set(await this.api<Evaluation>('evaluations', {})); }); }
}
bootstrapApplication(App).catch(console.error);
