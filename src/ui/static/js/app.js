/* ═══════════════════════════════════════════════════════════════════════
   CAM Intelligence Platform — v2.0 (Alpine.js)
   ═══════════════════════════════════════════════════════════════════════ */

/* Company/case lists fetched within this window are reused when moving between pages. */
const NAV_CACHE_MS = 10000;

function camApp() {
  // Kept outside the reactive component: Alpine proxies component state, which breaks Promises.
  let companiesLoadedAt = 0;
  let companiesInflight = null;

  return {
    /* Page modules (src/ui/static/js/modules/*.js, loaded before this file). */
    ...camFormatters(),
    ...camDashboard(),
    ...camJourney(),
    ...camPipeline(),
    ...camCaseDetail(),
    ...camDocuments(),
    ...camReports(),
    ...camApprovals(),
    ...camSettings(),

    /* ─── Core State ───────────────────────────────────────────────── */
    page: 'dashboard',
    loading: false,

    /* Toast */
    toast: '',
    toastType: '',
    _toastTimer: null,

    /* Dashboard */
    dash: {},

    /* Companies & Cases */
    companies: [],
    caseMap: {},

    /* Detail */
    detail: null,
    dtab: 'summary',
    detailExtraction: null,
    detailETB: null,
    detailDocs: null,
    detailFraud: null,
    detailPep: null,
    detailRuns: [],

    /* Companies with a downloadable document pack (GET /companies/supported-downloads) */
    supportedDownloadIds: [],

    /* Approval workflow */
    approvalStatus: null,
    approvalLevels: [],
    approvalMakerRoles: [],
    approvalRole: '',
    approvalUserId: '',
    approvalComments: '',
    approvalConditions: '',
    approvalQueue: [],

    /* Config / Settings */
    cfg: {},
    cfgSector: '',
    cfgSectorData: null,
    settingsTab: 'llm',
    probeStatus: null,
    reportProbe: null,

    /* LLM */
    llmProviders: [],
    llmActive: 'mock',
    narrativeMode: 'template',
    activeProvider: 'mock',
    llmTestResult: '',

    /* Engines */
    engines: [],

    /* Pipeline */
    agents: [],
    pipelineTarget: '',
    pipelineRunning: false,
    pipelineError: false,
    agentEvents: [],
    agentViewOpen: true,
    agentProgress: '',
    agentPct: 0,
    pipelineDoneResult: null,
    camBuildSections: [],

    /* Smart Onboard */
    enumVals: {},
    onboardMode: 'smart',
    onboardPick: '',            /* entity_id from the borrower dropdown, or '__other__' */
    onboardId: '',
    onboardFacility: 'working_capital',
    onboardAmount: null,
    onboardPurpose: '',
    onboardCaseType: 'NTB',
    onboardCrilcAvailable: false,
    journeyStage: 'select',
    etbLookupResult: null,
    etbLookupError: '',
    onboardResult: null,
    resolvePreview: null,

    /* Reports */
    reportEntity: '',
    reportTab: 'cam',
    reportLoading: false,
    camHtml: '',
    camSections: [],
    camActiveSection: 0,
    camComments: {},
    camCommentDrafts: {},
    camCommentSaving: false,
    camEditMode: false,
    camSectionEdits: {},
    camEditSaving: false,
    memoHtml: '',
    view360Data: null,
    v360tab: 'overview',
    chatMessages: [],
    chatInput: '',
    chatLoading: false,

    /* Documents Workspace */
    docEntity: '',
    docLoading: false,
    docUploading: false,
    docExtracting: false,
    docData: null,
    docGaps: null,
    docExtraction: null,
    docProbe: null,
    refDocs: {},
    docOpsHistory: [],
    docUploadCategory: 'financials',

    /* Manual Add Company */
    newCo: {
      entity_id: '', company_name: '', cin: '', pan: '',
      sector: '', borrower_type: 'unlisted', date_of_incorporation: '',
      credit_rating: '', rating_agency: '', employee_count: null,
      case_type: 'NTB', facility_type: 'working_capital',
      amount_requested_cr: null, purpose: '', tenor_months: null,
      existing_limit_cr: null,
      line_items: {
        revenue: null, ebitda: null, pat: null, total_debt: null,
        net_worth: null, total_assets: null, current_assets: null,
        current_liabilities: null, cash_and_equivalents: null,
        interest_expense: null, depreciation: null, tax_expense: null,
        inventory: null, trade_receivables: null, trade_payables: null,
      },
      collateral_type: '', collateral_desc: '',
      collateral_market_value: null, collateral_fsv: null,
    },

    /* Charts */
    _gradeChart: null,
    _scoreChart: null,

    /* ─── Core: start-up, navigation, API helper, shared company/case data ─── */
    /* Alpine calls init() itself — the page must not also use x-init="init()". */
    async init() {
      window.addEventListener('hashchange', () => this.onHash());
      // Reference data used across pages, loaded once; the current page loads its own data.
      await Promise.all([
        this.onHash(),
        this.loadConfig(),
        this.loadLLM(),
        this.loadEngines(),
        this.loadAgents(),
        this.loadEnums(),
        this.loadProbeStatus(),
        this.loadSupportedDownloads(),
        this.loadApprovalMatrix(),
      ]);
    },

    /* The URL hash is the single trigger for page loads (navigate() only changes it). */
    onHash() {
      const h = location.hash.slice(1) || 'dashboard';
      if (h.startsWith('case/')) {
        const eid = h.split('/')[1];
        // viewCase() sets this hash itself; don't load the same case a second time.
        if (this.page === 'detail' && this.detail?.entity_id === eid) return Promise.resolve();
        return Promise.all([this.loadCompanies({ maxAgeMs: NAV_CACHE_MS }), this.viewCase(eid)]);
      }
      this.page = h;
      return this.loadPage(h);
    },

    navigate(p) {
      this.page = p;
      if (location.hash.slice(1) !== p) location.hash = p;  // fires hashchange → onHash → loadPage
      else this.loadPage(p);                                 // same page clicked again: refresh it
    },

    /* Data each page needs. Company/case lists younger than NAV_CACHE_MS are reused,
       so moving between pages does not refetch them; actions that change data
       (runs, uploads, onboarding) call loadCompanies()/loadCases() directly for fresh data. */
    async loadPage(p) {
      const shared = () => this.loadCompanies({ maxAgeMs: NAV_CACHE_MS });
      if (p === 'dashboard') await Promise.all([this.loadDashboard(), shared()]);
      if (p === 'cases' || p === 'pipeline') await shared();
      if (p === 'documents') { await shared(); await this.loadDocumentWorkspace(); }
      if (p === 'onboard') await Promise.all([shared(), this.loadEnums(), this.loadProbeStatus()]);
      if (p === 'reports') {
        await shared();
        const executed = this.companies.filter(c => this.caseMap[c.entity_id]);
        if (!this.reportEntity && executed.length) this.reportEntity = executed[0].entity_id;
        await this.loadReportProbe();
        if (this.reportTab === 'approval') await this.loadApproval();
      }
      if (p === 'settings') await Promise.all([this.loadConfig(), this.loadLLM(), this.loadEngines()]);
    },

    notify(msg, type) {
      this.toast = msg;
      this.toastType = type === 'error' ? 'toast-err' : 'toast-ok';
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => this.toast = '', 3500);
    },

    /* ─── API Helpers ──────────────────────────────────────────────── */
    /* quiet: for optional lookups whose 404 just means "not run yet" — no error toast. */
    async api(path, opts, { quiet = false } = {}) {
      try {
        const r = await fetch('/api/' + path, opts);
        if (!r.ok) {
          const e = await r.json().catch(() => ({}));
          throw new Error(e.detail || r.statusText);
        }
        return await r.json();
      } catch (e) {
        if (!quiet) this.notify(e.message, 'error');
        throw e;
      }
    },

    jsonBody(method, body) {
      return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    },

    async loadProbeStatus() {
      try {
        this.probeStatus = await this.api('probe/status');
      } catch {
        this.probeStatus = null;
      }
    },

    /* ─── Companies / Cases ────────────────────────────────────────── */
    /* maxAgeMs (navigation only): skip if loaded that recently, or join a load already
       under way. Without it — after runs, uploads, onboarding — always fetch fresh. */
    async loadCompanies({ maxAgeMs = 0 } = {}) {
      if (maxAgeMs) {
        if (Date.now() - companiesLoadedAt < maxAgeMs) return;
        if (companiesInflight) return companiesInflight;
      }
      const load = this._fetchCompanies();
      companiesInflight = load;
      try {
        await load;
        companiesLoadedAt = Date.now();
      } finally {
        if (companiesInflight === load) companiesInflight = null;
      }
    },

    async _fetchCompanies() {
      const r = await this.api('companies');
      this.companies = r.companies || [];
      if (this.companies.length && !this.pipelineTarget) {
        this.pipelineTarget = this.companies[0].entity_id;
      }
      if (this.companies.length && !this.docEntity) {
        this.docEntity = this.companies[0].entity_id;
      }
      if (this.companies.length && !this.reportEntity) {
        this.reportEntity = this.companies[0].entity_id;
      }
      await this.loadCases();
      const executed = this.companies.filter(c => this.caseMap[c.entity_id]);
      if ((!this.reportEntity || !this.caseMap[this.reportEntity]) && executed.length) {
        this.reportEntity = executed[0].entity_id;
      }
    },

    async loadCases() {
      const r = await this.api('cases');
      const map = {};
      for (const c of (r.cases || [])) map[c.entity_id] = c;
      this.caseMap = map;
      // Update has_result on companies
      for (const c of this.companies) c.has_result = !!map[c.entity_id];
      // The score chart reads case summaries, which can arrive after the dashboard payload.
      if (this.page === 'dashboard') this.$nextTick(() => this.drawCharts());
    },

    /* ─── Executed-case helpers (used across pages) ─── */
    executedCompanies() {
      return this.companies.filter(c => !!this.caseMap[c.entity_id]);
    },

    hasExecutedCases() {
      return this.executedCompanies().length > 0;
    },

    selectedCompany(entityId) {
      const target = entityId || this.pipelineTarget || this.docEntity || this.reportEntity;
      return this.companies.find(c => c.entity_id === target) || null;
    },

    async loadEnums() {
      try { this.enumVals = await this.api('enums'); } catch {}
    },
  };
}
