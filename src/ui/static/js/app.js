/* ═══════════════════════════════════════════════════════════════════════
   CAM Intelligence Platform — v2.0 (Alpine.js)
   ═══════════════════════════════════════════════════════════════════════ */

function camApp() {
  return {
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
    bulkDocRun: null,

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

    /* ─── Init ─────────────────────────────────────────────────────── */
    async init() {
      window.addEventListener('hashchange', () => this.onHash());
      this.onHash();
      await Promise.all([
        this.loadDashboard(),
        this.loadCompanies(),
        this.loadConfig(),
        this.loadLLM(),
        this.loadEngines(),
        this.loadAgents(),
        this.loadEnums(),
        this.loadProbeStatus(),
      ]);
      if (this.page === 'documents') {
        await this.loadDocumentWorkspace();
      }
      if (this.page === 'reports') {
        const executed = this.companies.filter(c => this.caseMap[c.entity_id]);
        if (!this.reportEntity && executed.length) this.reportEntity = executed[0].entity_id;
        await this.loadReportProbe();
      }
    },

    onHash() {
      const h = location.hash.slice(1) || 'dashboard';
      if (h.startsWith('case/')) {
        this.viewCase(h.split('/')[1]);
      } else {
        this.page = h;
        if (h === 'documents') {
          this.loadCompanies().then(() => this.loadDocumentWorkspace());
        }
        if (h === 'reports') {
          this.loadCompanies().then(async () => {
            const executed = this.companies.filter(c => this.caseMap[c.entity_id]);
            if (!this.reportEntity && executed.length) this.reportEntity = executed[0].entity_id;
            await this.loadReportProbe();
          });
        }
      }
    },

    navigate(p) {
      this.page = p;
      location.hash = p;
      if (p === 'dashboard') this.loadDashboard();
      if (p === 'cases') { this.loadCompanies(); this.loadCases(); }
      if (p === 'documents') { this.loadCompanies().then(() => this.loadDocumentWorkspace()); }
      if (p === 'pipeline') { this.loadCompanies(); this.loadCases(); }
      if (p === 'onboard') { this.loadEnums(); this.loadCompanies(); }
      if (p === 'reports') { this.loadCompanies().then(() => this.loadReportProbe()); }
      if (p === 'settings') { this.loadConfig(); this.loadLLM(); this.loadEngines(); }
      if (p === 'onboard') { this.loadProbeStatus(); }
    },

    notify(msg, type) {
      this.toast = msg;
      this.toastType = type === 'error' ? 'toast-err' : 'toast-ok';
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => this.toast = '', 3500);
    },

    /* ─── API Helpers ──────────────────────────────────────────────── */
    async api(path, opts) {
      try {
        const r = await fetch('/api/' + path, opts);
        if (!r.ok) {
          const e = await r.json().catch(() => ({}));
          throw new Error(e.detail || r.statusText);
        }
        return await r.json();
      } catch (e) {
        this.notify(e.message, 'error');
        throw e;
      }
    },

    async loadProbeStatus() {
      try {
        this.probeStatus = await this.api('probe/status');
      } catch {
        this.probeStatus = null;
      }
    },

    async loadReportProbe() {
      if (!this.reportEntity) {
        this.reportProbe = null;
        return;
      }
      try {
        this.reportProbe = await this.api('companies/' + this.reportEntity + '/probe');
      } catch {
        this.reportProbe = { available: false };
      }
    },

    /* ─── Dashboard ────────────────────────────────────────────────── */
    async loadDashboard() {
      this.dash = await this.api('dashboard');
      this.$nextTick(() => this.drawCharts());
    },

    drawCharts() {
      /* Grade distribution */
      const gd = this.dash.grade_distribution || {};
      const grades = ['A','B','C','D','E'];
      const gColors = ['#10b981','#3b82f6','#f59e0b','#ef4444','#991b1b'];
      const gData = grades.map(g => gd[g] || 0);

      const gCtx = document.getElementById('gradeChart');
      if (gCtx) {
        if (this._gradeChart) this._gradeChart.destroy();
        this._gradeChart = new Chart(gCtx, {
          type: 'doughnut',
          data: {
            labels: grades.map(g => 'Grade ' + g),
            datasets: [{ data: gData, backgroundColor: gColors, borderWidth: 0 }],
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
              legend: { position: 'right', labels: { color: '#8888aa', font: { size: 12 } } }
            }
          }
        });
      }

      /* Score breakdown from most recent case */
      const rc = this.dash.recent_cases;
      if (rc && rc.length) {
        const latest = this.caseMap[rc[0].entity_id];
        if (latest) {
          const sCtx = document.getElementById('scoreChart');
          if (sCtx) {
            if (this._scoreChart) this._scoreChart.destroy();
            this._scoreChart = new Chart(sCtx, {
              type: 'bar',
              data: {
                labels: ['Financial','Conduct','Governance','Market','Composite'],
                datasets: [{
                  data: [latest.financial_score, latest.conduct_score,
                         latest.governance_score, latest.market_score, latest.composite_score],
                  backgroundColor: ['#3b82f6','#8b5cf6','#06b6d4','#f59e0b','#10b981'],
                  borderRadius: 4,
                }]
              },
              options: {
                responsive: true, maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {
                  x: { max: 100, ticks: { color: '#555578' }, grid: { color: '#252550' } },
                  y: { ticks: { color: '#8888aa' }, grid: { display: false } },
                },
                plugins: { legend: { display: false } },
              }
            });
          }
        }
      }
    },

    /* ─── Companies / Cases ────────────────────────────────────────── */
    async loadCompanies() {
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

    async loadExecutedCompanies() {
      const r = await this.api('companies?executed_only=true');
      return r.companies || [];
    },

    async loadCases() {
      const r = await this.api('cases');
      const map = {};
      for (const c of (r.cases || [])) map[c.entity_id] = c;
      this.caseMap = map;
      // Update has_result on companies
      for (const c of this.companies) c.has_result = !!map[c.entity_id];
    },

    async runOne(eid) {
      this.loading = true;
      try {
        await this.api('cases/' + eid + '/run', { method: 'POST' });
        this.notify(eid + ' analysis completed', 'ok');
        await this.loadCases();
        await this.loadDashboard();
      } catch {} finally { this.loading = false; }
    },

    async runAll() {
      this.loading = true;
      try {
        const r = await this.api('pipeline/run-all', { method: 'POST' });
        this.notify('All ' + (r.results?.length || 0) + ' companies analysed', 'ok');
        await this.loadCases();
        await this.loadDashboard();
      } catch {} finally { this.loading = false; }
    },

    async viewCase(eid) {
      this.loading = true;
      try {
        this.detail = await this.api('cases/' + eid);
        this.dtab = 'summary';
        this.page = 'detail';
        location.hash = 'case/' + eid;
        // Load extraction and ETB data if available
        this.detailExtraction = null;
        this.detailETB = null;
        try { this.detailExtraction = await this.api('companies/' + eid + '/extraction'); } catch {}
        if (String(this.detail?.case_type || '').toUpperCase() === 'ETB') {
          try { this.detailETB = await this.api('companies/' + eid + '/etb-analytics'); } catch {}
        }
        try { this.detailDocs = await this.api('companies/' + eid + '/documents'); } catch {}
      } catch {
        this.notify('Run the pipeline for this company first', 'error');
      } finally { this.loading = false; }
    },

    async generateDocumentsForDetail() {
      if (!this.detail?.entity_id) return;
      this.loading = true;
      try {
        const result = await this.api('companies/' + this.detail.entity_id + '/fetch-documents', { method: 'POST' });
        this.detailDocs = await this.api('companies/' + this.detail.entity_id + '/documents');
        if (this.docEntity === this.detail.entity_id) await this.loadDocumentOperations(this.detail.entity_id);
        this.notify('Generated ' + (result.files_generated?.length || 0) + ' document artifacts for ' + this.detail.entity_id, 'ok');
      } catch {} finally { this.loading = false; }
    },

    async generateAllSupportedDocumentPacks() {
      this.loading = true;
      try {
        this.bulkDocRun = await this.api('companies/fetch-documents/bulk', { method: 'POST' });
        await this.loadDocumentOperations();
        if (this.detail?.entity_id) {
          try { this.detailDocs = await this.api('companies/' + this.detail.entity_id + '/documents'); } catch {}
        }
        if (this.docEntity) {
          try { this.docData = await this.api('companies/' + this.docEntity + '/documents'); } catch {}
        }
        this.notify('Bulk document backfill complete: ' + (this.bulkDocRun?.total_generated || 0) + ' generated, ' + (this.bulkDocRun?.total_skipped || 0) + ' skipped', 'ok');
      } catch {} finally { this.loading = false; }
    },

    /* ─── Config ───────────────────────────────────────────────────── */
    async loadConfig() {
      this.cfg = await this.api('config');
      const sectors = Object.keys(this.cfg.benchmarks?.sectors || {});
      if (sectors.length && !this.cfgSector) this.cfgSector = sectors[0];
      this.loadBenchmarkSector();
    },

    loadBenchmarkSector() {
      const s = this.cfg.benchmarks?.sectors?.[this.cfgSector];
      // deep clone so edits don't mutate original until save
      this.cfgSectorData = s ? JSON.parse(JSON.stringify(s)) : null;
    },

    async saveBenchmarks() {
      if (!this.cfgSectorData) return;
      this.cfg.benchmarks.sectors[this.cfgSector] = this.cfgSectorData;
      await this.api('config/benchmarks', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.cfg.benchmarks),
      });
      this.notify('Benchmarks saved for ' + this.cfgSector, 'ok');
    },

    async saveRules() {
      await this.api('config/rules', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.cfg.rules),
      });
      this.notify('Rules saved', 'ok');
    },

    /* ─── LLM ──────────────────────────────────────────────────────── */
    async loadLLM() {
      const r = await this.api('llm/providers');
      this.llmProviders = r.providers || [];
      this.llmActive = r.active_provider || 'mock';
      this.narrativeMode = r.narrative_mode || 'template';
      this.activeProvider = this.llmActive;
    },

    async setLLM() {
      await this.api('llm/active', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: this.llmActive, narrative_mode: this.narrativeMode }),
      });
      this.activeProvider = this.llmActive;
      this.notify('LLM set to ' + this.llmActive + ' / ' + this.narrativeMode, 'ok');
    },

    async testLLM() {
      this.llmTestResult = 'Testing…';
      const r = await this.api('llm/test', { method: 'POST' });
      this.llmTestResult = r.status === 'ok' ? 'Connected' : ('Error: ' + (r.message || 'unknown'));
    },

    /* ─── Engines ──────────────────────────────────────────────────── */
    async loadEngines() {
      const r = await this.api('engines');
      this.engines = r.engines || [];
    },

    async toggleEngine(name) {
      await this.api('engines/' + name + '/toggle', { method: 'PUT' });
      await this.loadEngines();
    },

    /* ─── Pipeline ─────────────────────────────────────────────────── */
    async loadAgents() {
      const r = await this.api('agents');
      this.agents = r.agents || [];
    },

    /* SSE-powered pipeline execution with live agent progress */
    runPipelineSSE() {
      if (!this.pipelineTarget || this.pipelineRunning) return;
      this.pipelineRunning = true;
      this.pipelineError = false;
      this.agentEvents = [];
      this.agentViewOpen = true;
      this.agentPct = 0;
      this.agentProgress = '';
      this.pipelineDoneResult = null;
      this.camBuildSections = [];

      const es = new EventSource('/api/cases/' + this.pipelineTarget + '/run-stream');

      es.onmessage = (e) => {
        try {
          const evt = JSON.parse(e.data);
          if (evt.type === 'agent_start' || evt.type === 'agent_complete' || evt.type === 'info') {
            this.agentEvents = [...this.agentEvents, evt];
            if (evt.step && evt.total) {
              this.agentProgress = 'Step ' + evt.step + ' / ' + evt.total;
              if (evt.type === 'agent_complete') {
                this.agentPct = Math.round((evt.step / evt.total) * 100);
              }
            }
          } else if (evt.type === 'section_start' || evt.type === 'section_complete') {
            this.agentEvents = [...this.agentEvents, evt];
            if (evt.step && evt.total) {
              this.agentProgress = 'Narrative: section ' + evt.step + ' / ' + evt.total + ' — ' + (evt.title || evt.section);
            }
            // Track section build progress
            if (evt.type === 'section_start') {
              const idx = this.camBuildSections.findIndex(s => s.id === evt.section);
              if (idx >= 0) {
                this.camBuildSections[idx].status = 'writing';
              } else {
                this.camBuildSections = [...this.camBuildSections, { id: evt.section, title: evt.title || evt.section, status: 'writing', step: evt.step, total: evt.total }];
              }
            } else {
              const idx = this.camBuildSections.findIndex(s => s.id === evt.section);
              if (idx >= 0) {
                this.camBuildSections[idx].status = 'done';
                this.camBuildSections = [...this.camBuildSections];
              } else {
                this.camBuildSections = [...this.camBuildSections, { id: evt.section, title: evt.title || evt.section, status: 'done', step: evt.step, total: evt.total }];
              }
            }
          } else if (evt.type === 'done') {
            this.agentPct = 100;
            this.agentProgress = 'Complete';
            this.pipelineDoneResult = {
              entity_id: this.pipelineTarget,
              recommendation: evt.recommendation,
              risk_grade: evt.risk_grade,
              composite_score: evt.composite_score,
              narrative_mode: evt.narrative_mode,
            };
            this.pipelineRunning = false;
            es.close();
            this.notify('Pipeline complete — ' + (evt.recommendation || '').replace(/_/g, ' '), 'ok');
            this.loadCases();
            this.loadDashboard();
          } else if (evt.type === 'error') {
            this.pipelineRunning = false;
            this.pipelineError = true;
            es.close();
            this.notify('Pipeline error: ' + (evt.message || 'unknown'), 'error');
          }
        } catch {}
      };

      es.onerror = () => {
        this.pipelineRunning = false;
        this.pipelineError = true;
        es.close();
        if (!this.pipelineDoneResult) {
          this.notify('Pipeline connection lost', 'error');
        }
      };
    },

    async runAllPipeline() {
      this.loading = true;
      try {
        const r = await this.api('pipeline/run-all', { method: 'POST' });
        this.notify('All ' + (r.results?.length || 0) + ' companies analysed', 'ok');
        await this.loadCases();
        await this.loadDashboard();
      } catch {} finally { this.loading = false; }
    },

    /* ─── Add Company ──────────────────────────────────────────────── */
    executedCompanies() {
      return this.companies.filter(c => !!this.caseMap[c.entity_id]);
    },

    hasExecutedCases() {
      return this.executedCompanies().length > 0;
    },

    pipelineRows() {
      return this.executedCompanies().slice().sort((a, b) => {
        if (a.entity_id === this.pipelineTarget) return -1;
        if (b.entity_id === this.pipelineTarget) return 1;
        const aScore = Number(this.caseMap[a.entity_id]?.composite_score || 0);
        const bScore = Number(this.caseMap[b.entity_id]?.composite_score || 0);
        if (bScore !== aScore) return bScore - aScore;
        return (a.company_name || '').localeCompare(b.company_name || '');
      });
    },

    selectedCompany(entityId) {
      const target = entityId || this.pipelineTarget || this.docEntity || this.reportEntity;
      return this.companies.find(c => c.entity_id === target) || null;
    },

    selectedPipelineCase() {
      return this.caseMap[this.pipelineTarget] || null;
    },

    avgExecutedScore() {
      const scores = this.executedCompanies()
        .map(c => Number(this.caseMap[c.entity_id]?.composite_score))
        .filter(v => !Number.isNaN(v) && v > 0);
      if (!scores.length) return '0.0';
      return (scores.reduce((sum, v) => sum + v, 0) / scores.length).toFixed(1);
    },

    recommendationCount(type) {
      return this.executedCompanies().filter(c => this.caseMap[c.entity_id]?.recommendation === type).length;
    },

    modeCount(mode) {
      return this.executedCompanies().filter(c => (this.caseMap[c.entity_id]?.narrative_mode || 'template') === mode).length;
    },

    companyInitials(name) {
      return (name || '')
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map(part => part[0])
        .join('')
        .toUpperCase() || '--';
    },

    humanizeText(value) {
      const raw = String(value || '').trim();
      if (!raw) return '';
      const tokenMap = {
        api: 'API',
        cam: 'CAM',
        cin: 'CIN',
        crilc: 'CRILC',
        epfo: 'EPFO',
        etb: 'ETB',
        gst: 'GST',
        it: 'IT',
        kyc: 'KYC',
        llm: 'LLM',
        mca: 'MCA',
        mcp: 'MCP',
        ntb: 'NTB',
        pan: 'PAN',
        pvt: 'Pvt',
        ltd: 'Ltd',
        limited: 'Limited',
        private: 'Private',
        public: 'Public',
        llp: 'LLP',
        llc: 'LLC',
        plc: 'PLC',
      };
      const lowerWords = new Set(['and', 'of', 'for', 'to', 'in', 'on', 'the']);
      return raw
        .replace(/_/g, ' ')
        .split(/\s+/)
        .map((token, index) => {
          const normalized = token.toLowerCase();
          if (normalized === 'the') return index === 0 ? 'The' : 'the';
          if (tokenMap[normalized]) return tokenMap[normalized];
          if (lowerWords.has(normalized) && index > 0) return normalized;
          if (!/[a-z]/.test(token) && /^[A-Z0-9&.-]{2,4}$/.test(token)) return token;
          return normalized.charAt(0).toUpperCase() + normalized.slice(1);
        })
        .join(' ');
    },

    displayCompanyName(value) {
      return this.humanizeText(value) || '--';
    },

    providerLabel(provider) {
      if (!provider) return 'Internal';
      if (provider === 'probe42_mcp_v2') return 'Verified Public Data';
      if (provider === 'mock_external') return 'External Data';
      return this.humanizeText(provider);
    },

    probeRecordLabel(key) {
      const labels = {
        base_details: 'Company master',
        open_charges: 'Open charges',
        kyc_details: 'KYC and directors',
        legal_history: 'Legal history',
        credit_ratings: 'Ratings',
        gst_details: 'GST profile',
        epfo_details: 'EPFO profile',
        suit_filed_cases: 'Suit-filed cases',
        director_network: 'Director network',
        data_status: 'Freshness',
      };
      return labels[key] || this.humanizeText(key);
    },

    probeRecordRows(snapshot) {
      const toolStatus = snapshot?.tool_status || {};
      return [
        'base_details',
        'kyc_details',
        'credit_ratings',
        'gst_details',
        'legal_history',
        'open_charges',
        'epfo_details',
        'suit_filed_cases',
        'director_network',
        'data_status',
      ].map((key) => ({
        key,
        label: this.probeRecordLabel(key),
        status: toolStatus[key] || 'not_fetched',
      }));
    },

    availableProbeRecordCount(snapshot) {
      return this.probeRecordRows(snapshot).filter(row => row.status === 'success').length;
    },

    sourceStatusLabel(status) {
      const value = (status || 'unknown').toLowerCase();
      if (value === 'success') return 'available';
      if (value === 'not_found') return 'not available';
      if (value === 'not_fetched') return 'not fetched';
      return this.humanizeText(value);
    },

    sourceStatusClass(status) {
      const value = (status || 'unknown').toLowerCase();
      if (value === 'success') return 'badge-green';
      if (value === 'not_found') return 'badge-amber';
      return 'badge-grey';
    },

    policyRuleLabel(code, fallbackDescription = '') {
      const labels = {
        HR_WILFUL_DEFAULTER: 'Wilful defaulter screening',
        HR_COMPANY_ACTIVE: 'Active company status',
        HR_NO_CRITICAL_EXCEPTIONS: 'Critical validation clearance',
        HR_KYC_COMPLETE: 'KYC package completeness',
        HR_BUREAU_STATUS: 'Public-record stress screening',
        HR_PUBLIC_RECORD_STATUS: 'Public-record stress screening',
        HR_MIN_VINTAGE: 'Minimum business vintage',
        HR_FRAUD_REGISTRY: 'Fraud registry screening',
        HR_RBI_DEFAULTER: 'RBI defaulter screening',
        HR_SUIT_FILED: 'Suit-filed exposure threshold',
      };
      return labels[code] || fallbackDescription || this.humanizeText(String(code || '').replace(/^HR_/, '').replace(/_/g, ' '));
    },

    exceptionLabel(code) {
      const labels = {
        XSRC_DEBT_BUREAU_MISMATCH: 'Debt vs public-record exposure mismatch',
        XSRC_BUREAU_DPD_ALERT: 'Public-record stress status alert',
        XSRC_BUREAU_WILFUL_DEFAULTER: 'Wilful defaulter alert',
        XSRC_REVENUE_MISMATCH: 'Cross-source revenue mismatch',
        DOC_REVENUE_CROSS_SOURCE: 'Document revenue mismatch',
        STRUCT_PAT_INCONSISTENT: 'PAT structure mismatch',
        STRUCT_EBITDA_INCONSISTENT: 'EBITDA structure mismatch',
      };
      return labels[code] || this.humanizeText(String(code || '').replace(/^(XSRC|DOC|STRUCT)_/, '').replace(/_/g, ' '));
    },

    presentationText(value) {
      return String(value || '')
        .replace(/\bBureau\b/g, 'Public-record')
        .replace(/\bbureau\b/g, 'public-record')
        .replace(/Wilful Defaulter in public-record records/g, 'Wilful Defaulter in public records')
        .replace(/â€”/g, '-')
        .replace(/—/g, '-');
    },

    titleCase(value) {
      return this.humanizeText(value);
    },

    caseTypeLabel(value) {
      const raw = String(value || '').trim();
      if (!raw) return '--';
      const upper = raw.toUpperCase();
      if (['NTB', 'ETB', 'TL', 'OD', 'CC', 'WC'].includes(upper)) return upper;
      return this.humanizeText(raw);
    },

    modeLabel(value) {
      const raw = String(value || '').trim();
      if (!raw) return 'Template';
      if (raw.toLowerCase() === 'llm') return 'LLM';
      if (raw.toLowerCase() === 'template') return 'Template';
      return this.humanizeText(raw);
    },

    displayScore(value) {
      const num = Number(value);
      if (Number.isNaN(num) || num <= 0) return '--';
      return Number.isInteger(num) ? num.toFixed(0) : num.toFixed(1);
    },

    cacheTtlLabel(hours) {
      const ttl = Number(hours || 0);
      if (!ttl) return 'Until deleted';
      if (ttl % 24 === 0) {
        const days = ttl / 24;
        return days === 1 ? '1 day' : (days + ' days');
      }
      return ttl + 'h';
    },

    formatCurrencyCr(value) {
      const num = Number(value || 0);
      if (!num) return '0 Cr';
      return 'Rs. ' + num.toLocaleString('en-IN', { maximumFractionDigits: num >= 100 ? 0 : 2 }) + ' Cr';
    },

    formatDecimal(value, digits = 1) {
      const num = Number(value);
      if (Number.isNaN(num)) return '--';
      return num.toLocaleString('en-IN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });
    },

    severityClass(severity) {
      const value = String(severity || '').toLowerCase();
      if (value === 'critical' || value === 'high') return 'badge-red';
      if (value === 'medium') return 'badge-amber';
      if (value === 'low') return 'badge-green';
      return 'badge-info';
    },

    severityCount(flags, severity) {
      const targets = Array.isArray(severity) ? severity : [severity];
      return (flags || []).filter(flag => targets.includes(String(flag?.severity || '').toLowerCase())).length;
    },

    stanceClass(stance) {
      const value = String(stance || '').toLowerCase();
      if (value.includes('favourable') || value.includes('positive')) return 'badge-green';
      if (value.includes('stable') || value.includes('mixed')) return 'badge-info';
      if (value.includes('watch')) return 'badge-amber';
      if (value.includes('cautious') || value.includes('negative')) return 'badge-red';
      return 'badge-grey';
    },

    documentUploadCoverageClass(value) {
      const num = Number(value || 0);
      if (num >= 75) return 'score-good';
      if (num >= 40) return 'score-mid';
      return 'score-bad';
    },

    documentCategoryStatus(info) {
      const required = Number(info?.upload_required_count || 0);
      const coverage = Number(info?.upload_coverage_pct || 0);
      const visibleDocs = (info?.items || []).filter(item => item.file_type === 'document').length;
      const extraFiles = (info?.legacy_items || []).length + (info?.system_items || []).length;
      if (required > 0) return coverage + '%';
      if (visibleDocs > 0) return 'Available';
      if (extraFiles > 0) return 'Available';
      return 'Optional';
    },

    documentCategoryStatusClass(info) {
      const required = Number(info?.upload_required_count || 0);
      const coverage = Number(info?.upload_coverage_pct || 0);
      const visibleDocs = (info?.items || []).filter(item => item.file_type === 'document').length;
      const extraFiles = (info?.legacy_items || []).length + (info?.system_items || []).length;
      if (required > 0) {
        if (coverage >= 75) return 'badge-green';
        if (coverage >= 40) return 'badge-amber';
        return 'badge-red';
      }
      if (visibleDocs > 0) return 'badge-green';
      if (extraFiles > 0) return 'badge-info';
      return 'badge-grey';
    },

    documentCategorySuggestionLabel(info) {
      return Number(info?.upload_required_count || 0) > 0 ? 'Required uploads' : 'If available';
    },

    documentCategorySuggestedItems(info) {
      if (Number(info?.upload_required_count || 0) > 0 && Array.isArray(info?.upload_missing_descriptions) && info.upload_missing_descriptions.length) {
        return info.upload_missing_descriptions;
      }
      return info?.missing || [];
    },

    documentCategoryEmptyMessage(info) {
      const extraFiles = (info?.legacy_items || []).length + (info?.system_items || []).length;
      if (extraFiles > 0) return 'No uploaded borrower files in this category yet.';
      return 'No files in this category yet.';
    },

    documentCategoryArchiveNote(info) {
      const extraFiles = (info?.legacy_items || []).length + (info?.system_items || []).length;
      if (!extraFiles) return '';
      return extraFiles + ' additional source/system files are available below. They do not count toward RM upload coverage.';
    },

    escapeHtml(value) {
      return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    },

    chatMessageHtml(content, role = 'assistant') {
      const text = this.presentationText(content);
      if (role === 'assistant') {
        return this.renderMd(text)
          .replace(/^<p>\s*<\/p>/, '')
          .replace(/<p>\s*<\/p>$/,'');
      }
      return this.escapeHtml(text).replace(/\n/g, '<br>');
    },

    formatRunTime(value) {
      if (!value) return 'Pending';
      const dt = new Date(value);
      if (Number.isNaN(dt.getTime())) return value;
      return dt.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      });
    },

    startCamJourney() {
      this.onboardMode = 'smart';
      this.journeyStage = 'select';
      this.resolvePreview = null;
      this.onboardResult = null;
      this.etbLookupResult = null;
      this.etbLookupError = '';
      this.onboardId = '';
      this.onboardPurpose = '';
      this.onboardAmount = null;
      this.onboardFacility = 'working_capital';
      this.onboardCaseType = 'NTB';
      this.onboardCrilcAvailable = false;
      this.navigate('onboard');
    },

    journeySteps() {
      return [
        { key: 'select', label: 'Journey' },
        { key: 'entity', label: 'Entity' },
        { key: 'retrieved', label: 'Verified Data' },
        { key: 'ready', label: 'Final CAM' },
      ];
    },

    journeyStepState(key) {
      const stageRank = {
        select: 0,
        entity: 1,
        aggregating: 1,
        retrieved: 2,
        prebuilt: 2,
        drafting: 3,
        ready: 3,
      };
      const current = stageRank[this.journeyStage] ?? 0;
      const target = stageRank[key] ?? 0;
      if (target < current) return 'done';
      if (target === current) return 'active';
      return 'upcoming';
    },

    selectJourney(mode) {
      this.onboardCaseType = mode;
      this.journeyStage = 'entity';
    },

    journeyEntityId() {
      return this.onboardResult?.entity_id || this.resolvePreview?.entity_id || this.pipelineTarget || this.reportEntity || '';
    },

    activeJourneyCase() {
      const entityId = this.journeyEntityId();
      return entityId ? (this.caseMap[entityId] || null) : null;
    },

    journeyCurrentCase() {
      const entityId = this.journeyEntityId();
      if (!entityId) return null;
      if (this.caseMap[entityId]) return this.caseMap[entityId];
      if (this.pipelineDoneResult?.entity_id === entityId) return this.pipelineDoneResult;
      return null;
    },

    journeySourceBadges() {
      return [
        'Company Registry Verified',
        'Identity Validated',
        'Tax Registration Checked',
        'Ratings & Legal Snapshot',
        this.probeStatus?.configured ? 'Connected Data Feed' : 'Cached Case Data',
      ];
    },

    journeyRetrievedInfo() {
      const preview = this.resolvePreview || {};
      const probe = this.onboardResult?.probe_summary || {};
      return [
        {
          title: 'Corporate Information',
          items: [
            'Legal Name: ' + (preview.company_name || 'Pending resolution'),
            'CIN: ' + (preview.cin || 'Not available'),
            'PAN: ' + (preview.pan || 'Not available'),
            'Listing Status: ' + (probe.listing_status || 'Not available'),
          ],
        },
        {
          title: 'Compliance & Registration',
          items: [
            'GSTIN: ' + (preview.gstin || 'Not available'),
            'Status: ' + (probe.status || 'Not available'),
            'Registry health: ' + (probe.compliance_status || 'Validated'),
            'Retention: Verified public records stay attached until removed',
          ],
        },
        {
          title: 'Directors & Management',
          items: [
            'Directors captured: ' + (probe.directors_count ?? 'Not available'),
            'KYC status: ' + (probe.kyc_status || 'Validated'),
            'Open charges: ' + (probe.open_charge_count ?? 'Not available'),
            'Legal cases: ' + (probe.legal_case_count ?? 'Not available'),
          ],
        },
        {
          title: 'Financial Filings Available',
          items: [
            'Ratings snapshot: ' + (probe.rating || 'Unrated'),
            'Validation mode: Public-record baseline + latest RM uploads override',
            'Requested facility: ' + this.titleCase(this.onboardFacility || 'working_capital'),
            'Coverage: ' + this.titleCase(this.onboardResult?.profile || this.probeStatus?.bundle_profile || 'full'),
          ],
        },
      ];
    },

    journeyRequiredUploads() {
      return [
        { title: 'Audited Financial Statements', roleKey: 'audited_financial_statements', category: 'financials', hint: 'Upload latest 3 years audited financials' },
        { title: 'Provisional Financials', roleKey: 'provisional_financials', category: 'financials', hint: 'Upload latest provisional or management financials' },
        { title: 'Debt Schedule', roleKey: 'debt_schedule', category: 'financials', hint: 'Upload detailed debt schedule & lender-wise exposure' },
        { title: 'Board Resolution', roleKey: 'board_resolution', category: 'kyc', hint: 'Upload board resolution / borrowing approval' },
        { title: 'CMA Or Projection', roleKey: 'cma_or_projection', category: 'request', hint: 'Upload CMA data / projections / repayment assumptions' },
      ];
    },

    journeyPendingRequiredCount() {
      const missing = this.docGaps?.required_missing_documents || [];
      return missing.length;
    },

    journeyMissingRequiredUploads() {
      const gaps = this.docGaps?.required_missing_documents || [];
      return gaps.map((item) => ({
        title: this.titleCase((item.type || 'document').replaceAll('_', ' ')),
        roleKey: item.type || '',
        category: item.category || 'misc',
        hint: item.description || 'Upload latest borrower-provided document',
      }));
    },

    journeyRetrievedDocuments() {
      const files = [];
      const categories = this.docData?.categories || {};
      Object.values(categories).forEach((info) => {
        (info.items || []).forEach((item) => {
          if (item.file_type !== 'document') return;
          files.push({
            filename: item.filename,
            category: item.category || '',
            displayLabel: item.document_role_label || this.humanizeText(item.category || 'document') || 'Document',
          });
        });
      });
      return files;
    },

    journeyVerifiedSourceCount() {
      const summary = this.onboardResult?.source_summary || {};
      const statuses = Object.values(summary).map(value => String(value || '').toLowerCase());
      const successCount = statuses.filter(value => value === 'success').length;
      if (successCount) return successCount;
      return this.onboardResult?.probe_summary ? 4 : 0;
    },

    journeyWorkspaceDocumentCount() {
      const storedCount = this.onboardResult?.documents_stored?.document_file_count;
      if (typeof storedCount === 'number') return storedCount;
      const visibleCount = this.docData?.document_file_count;
      if (typeof visibleCount === 'number') return visibleCount;
      return this.journeyRetrievedDocuments().length;
    },

    journeyVerifiedCoverageLabel() {
      const verified = this.journeyVerifiedSourceCount();
      if (verified >= 9) return 'Comprehensive';
      if (verified >= 6) return 'Strong';
      if (verified >= 3) return 'Partial';
      return 'Pending';
    },

    documentCategoryEntries(categories) {
      return Object.entries(categories || {}).filter(([, info]) => {
        const visibleDocuments = (info.items || []).filter(item => item.file_type === 'document');
        return visibleDocuments.length > 0 || (info.missing || []).length > 0;
      });
    },

    journeyOptionalInputs() {
      return [
        {
          key: 'site_visit_report',
          title: 'Site Visit Report',
          category: 'request',
          hint: 'Branch visit notes, promoter meetings, and operating observations.',
          sourceHint: 'RM, branch team, or field visit partner',
          camSection: '2. Borrower Profile / 7. Risk Assessment',
        },
        {
          key: 'valuation_report',
          title: 'Valuation Report',
          category: 'collateral',
          hint: 'Security valuation, FSV assumptions, and collateral comfort.',
          sourceHint: 'Empanelled valuer or collateral team',
          camSection: '6. Security & Collateral',
        },
        {
          key: 'bank_statements',
          title: 'Bank Statements',
          category: 'banking',
          hint: 'Latest operating account conduct and cash flow validation.',
          sourceHint: 'Borrower bank statements or internal CBS for ETB cases',
          camSection: '10. Account Conduct',
        },
        {
          key: 'financial_projections',
          title: 'Financial Projections',
          category: 'request',
          hint: 'CMA, projected cash flows, and repayment assumptions.',
          sourceHint: 'Borrower CFO pack, CMA data, or RM projections sheet',
          camSection: '4. Financial Analysis / 5. Facility Details',
        },
        {
          key: 'credit_facility_details',
          title: 'Credit Facility Details',
          category: 'banking',
          hint: 'Existing sanctions, limits, and lender-wise exposure.',
          sourceHint: 'Internal LMS, sanction tracker, or lender-wise exposure note',
          camSection: '5. Credit Facility Details',
        },
        {
          key: 'internal_credit_notes',
          title: 'Internal Credit Notes',
          category: 'misc',
          hint: 'RM or analyst notes that strengthen the approval narrative.',
          sourceHint: 'RM, analyst, branch credit desk, or sanction memo',
          camSection: '1. Executive Summary / 12. Recommendation',
        },
        {
          key: 'property_documents',
          title: 'Property Documents',
          category: 'collateral',
          hint: 'Title deed, search report, and encumbrance certificate.',
          sourceHint: 'Collateral team / empanelled valuer / legal department',
          camSection: '6. Security & Collateral',
        },
        {
          key: 'cersai_search',
          title: 'CERSAI Search Report',
          category: 'legal',
          hint: 'Central registry search for existing security interests.',
          sourceHint: 'Central Registry (CERSAI) / legal & compliance team',
          camSection: '6. Security & Collateral',
        },
        {
          key: 'insurance_policies',
          title: 'Insurance Policies',
          category: 'collateral',
          hint: 'Property, stock, and key man insurance coverage.',
          sourceHint: 'Borrower / insurance broker / risk management team',
          camSection: '6. Security & Collateral / 7. Risk Assessment',
        },
        {
          key: 'undertakings',
          title: 'Undertakings & Declarations',
          category: 'legal',
          hint: 'Non-default declaration, information consent, end-use undertaking.',
          sourceHint: 'Borrower / Company Secretary / legal team',
          camSection: '8. Compliance / 12. Recommendation',
        },
        {
          key: 'board_resolution_borrowing',
          title: 'Board Resolution — Borrowing',
          category: 'kyc',
          hint: 'Board resolution authorising borrowing powers.',
          sourceHint: 'Company Secretary / legal team',
          camSection: '8. Compliance',
        },
      ];
    },

    /* Unified document checklist — merges retrieved, required, and optional into one list */
    journeyAllDocuments() {
      const rows = [];
      const claimedFiles = new Set();

      /* Build all visible files from docData */
      const allFiles = [];
      const categories = this.docData?.categories || {};
      Object.values(categories).forEach((info) => {
        (info.items || []).forEach((item) => {
          if (item.file_type !== 'document') return;
          allFiles.push({
            filename: item.filename,
            category: (item.category || '').toLowerCase(),
            document_role: item.document_role || '',
            document_role_label: item.document_role_label || '',
            source: item.source || '',
          });
        });
      });

      /* Claim files matching a role key within a category */
      const claimFiles = (category, roleKey) => {
        const catKey = (category || '').toLowerCase();
        const matched = [];
        allFiles.forEach((f) => {
          const key = f.category + '/' + f.filename;
          if (claimedFiles.has(key)) return;
          if (f.category !== catKey) return;
          if (roleKey && f.document_role === roleKey) {
            matched.push(f);
            claimedFiles.add(key);
          }
        });
        return matched;
      };

      /* 1. Required RM uploads — match files by document_role */
      const required = this.journeyRequiredUploads();
      required.forEach((doc) => {
        const matches = claimFiles(doc.category, doc.roleKey);
        rows.push({
          title: doc.title,
          status: matches.length > 0 ? 'uploaded' : 'missing',
          statusLabel: matches.length > 0 ? matches.length + ' file(s)' : doc.hint,
          camSection: '',
          category: doc.category,
          canUpload: true,
          group: 'required',
          roleKey: doc.roleKey,
          files: matches,
        });
      });

      /* 2. Optional / additional inputs — match files by key */
      this.journeyOptionalInputs().forEach((doc) => {
        const matches = claimFiles(doc.category, doc.key);
        rows.push({
          title: doc.title,
          status: matches.length > 0 ? 'uploaded' : 'pending',
          statusLabel: matches.length > 0 ? matches.length + ' file(s)' : doc.hint,
          camSection: doc.camSection,
          category: doc.category,
          canUpload: true,
          group: 'optional',
          key: doc.key,
          files: matches,
        });
      });

      /* 3. Unclaimed files — group by document_role or category */
      const unclaimed = allFiles.filter((f) => !claimedFiles.has(f.category + '/' + f.filename));
      const groups = {};
      unclaimed.forEach((f) => {
        const groupKey = f.document_role || f.category;
        if (!groups[groupKey]) groups[groupKey] = { files: [], category: f.category, label: f.document_role_label || this.humanizeText(f.category) || 'Other' };
        groups[groupKey].files.push(f);
      });
      Object.values(groups).forEach((g) => {
        rows.push({
          title: g.label,
          status: 'available',
          statusLabel: g.files.length + ' file(s)',
          camSection: '',
          category: g.category,
          canUpload: true,
          group: 'retrieved',
          files: g.files,
        });
      });

      return rows;
    },

    journeyReviewStats() {
      const activeCase = this.journeyCurrentCase() || {};
      const factPack = activeCase.fact_pack || {};
      const keyRisks = Array.isArray(factPack.key_risks) ? factPack.key_risks.length : 0;
      const policyFlags = Array.isArray(activeCase.exceptions) ? activeCase.exceptions.length : 0;
      const sectionsValidated = this.camSections.length || 12;
      return [
        { value: keyRisks || 0, label: 'Key risk signals identified' },
        { value: policyFlags || 0, label: 'Policy deviations requiring review' },
        { value: sectionsValidated, label: 'Sections validated and structured' },
      ];
    },

    dashboardApprovalRate() {
      const total = this.executedCompanies().length;
      if (!total) return '0%';
      const approvals = this.recommendationCount('approve') + this.recommendationCount('conditional_approve');
      return Math.round((approvals / total) * 100) + '%';
    },

    dashboardHighRiskCount() {
      return this.executedCompanies().filter(c => ['C', 'D', 'E'].includes(this.caseMap[c.entity_id]?.risk_grade)).length;
    },

    dashboardPrimaryStat() {
      if (!this.hasExecutedCases()) {
        return {
          label: 'Borrowers Ready',
          value: this.companies.length,
        };
      }
      return {
        label: 'CAMs in Progress',
        value: this.executedCompanies().filter(c => {
          const recommendation = this.caseMap[c.entity_id]?.recommendation;
          return recommendation !== 'approve' && recommendation !== 'conditional_approve';
        }).length,
      };
    },

    dashboardFeatureCards() {
      return [
        { title: 'AI Data Aggregation', copy: 'Unified ingestion from public records, uploaded documents, and internal banking inputs.' },
        { title: 'Financial & Risk Analysis', copy: 'Ratios, trend scans, validation exceptions, and risk indicators in one credit view.' },
        { title: 'CAM Auto-Generation', copy: 'Structured CAM drafts generated section-wise with policy aligned formatting.' },
        { title: 'Decision Support', copy: 'Scorecards, conditions, and recommendation logic ready for analyst review.' },
        { title: 'Workflow & Compliance', copy: 'RM gaps, upload tracking, comments, and traceable case progression.' },
      ];
    },

    dashboardPipelineColumns() {
      if (!this.hasExecutedCases()) {
        return [
          { title: 'Intake Queue', items: [] },
          { title: 'Analysis', items: [] },
          { title: 'Drafting', items: [] },
          { title: 'Review / Approval', items: [] },
        ];
      }
      const executed = this.pipelineRows();
      const fmtItem = (company, status) => ({
        entity_id: company.entity_id,
        company_name: this.displayCompanyName(company.company_name),
        subtitle: this.titleCase(company.facility_type || 'working_capital') + ' • ' + this.formatCurrencyCr(company.requested_amount_cr || 0),
        meta: status + ' • ' + (this.caseMap[company.entity_id]?.run_at ? this.formatRunTime(this.caseMap[company.entity_id]?.run_at) : 'Run completed'),
      });
      const referred = executed.filter(c => ['refer', 'decline'].includes(this.caseMap[c.entity_id]?.recommendation));
      const approved = executed.filter(c => ['approve', 'conditional_approve'].includes(this.caseMap[c.entity_id]?.recommendation));
      const narrated = executed.filter(c => (this.caseMap[c.entity_id]?.narrative_mode || 'template') === 'llm');
      return [
        { title: 'Recently Executed', items: executed.slice(0, 2).map(c => fmtItem(c, 'Case executed')) },
        { title: 'Needs Review', items: referred.slice(0, 2).map(c => fmtItem(c, 'Analyst review required')) },
        { title: 'Narrative Ready', items: narrated.slice(0, 2).map(c => fmtItem(c, 'Narrative prepared')) },
        { title: 'Decisioned', items: approved.slice(0, 2).map(c => fmtItem(c, 'Decision available')) },
      ];
    },

    dashboardPipelineEmptyMessage() {
      if (!this.companies.length) {
        return 'No borrowers are loaded yet. Add a borrower or restore the company catalog to begin.';
      }
      return 'No live CAM cases yet. Start a CAM journey or run the pipeline for one borrower to create the first case.';
    },

    dashboardRiskAlerts() {
      if (!this.hasExecutedCases()) {
        return [
          'No case risk alerts yet because no borrower has been executed',
          'Verified public records are ready for the first run',
          'Upload the latest RM documents before execution if fresher borrower files are available',
        ];
      }
      const alerts = [];
      this.pipelineRows().slice(0, 3).forEach((company) => {
        const detail = this.caseMap[company.entity_id] || {};
        const grade = detail.risk_grade || 'N/A';
        if (grade === 'A' || grade === 'B') return;
        const exception = Array.isArray(detail.exceptions) && detail.exceptions.length
          ? (detail.exceptions[0]?.message || detail.exceptions[0]?.exception_code || 'Validation exception flagged')
          : 'Credit risk requires closer review';
        alerts.push(this.displayCompanyName(company.company_name) + ' • ' + exception);
      });
      return alerts.length ? alerts : [
        'No high-risk alerts open right now',
        'Document coverage gaps are being tracked separately',
        'Verified public records remain attached to the borrower record',
      ];
    },

    dashboardInsights() {
      if (!this.hasExecutedCases()) {
        return [
          this.companies.length
            ? (this.companies.length + ' borrowers are ready to be used for the first CAM run')
            : 'No borrowers are loaded yet for CAM execution',
          'Use CAM Journey to review verified public data and add the latest RM uploads before execution',
          'Verified public records stay attached until they are explicitly removed',
        ];
      }
      return [
        this.executedCompanies().length
          ? (this.executedCompanies().length + ' CAMs now have reusable case intelligence and verified public context')
          : 'Start a CAM journey to seed the first verified case',
        this.onboardResult?.missing_documents?.length
          ? (this.onboardResult.missing_documents.length + ' borrower documents are still pending for the current journey')
          : 'Document gaps are isolated to RM uploads rather than repeat public-data pulls',
        'Verified public records stay attached until they are explicitly removed',
      ];
    },

    recentExecutedCases() {
      return Object.values(this.caseMap)
        .slice()
        .sort((a, b) => (b.run_at || '').localeCompare(a.run_at || ''))
        .slice(0, 4);
    },

    assignedCases() {
      const labels = ['Today', 'Tomorrow', '+2 days', '+3 days'];
      return this.pipelineRows().slice(0, 4).map((company, idx) => ({
        company_name: this.displayCompanyName(company.company_name),
        priority: idx === 0 ? 'High' : idx < 3 ? 'Medium' : 'Low',
        stage: (this.caseMap[company.entity_id]?.recommendation ? 'Final Review' : 'Data Ingestion'),
        due: labels[idx] || '+5 days',
      }));
    },

    pipelineEmptyStateMessage() {
      const company = this.selectedCompany();
      if (!company) {
        return 'No borrower selected. Choose a borrower to start the first pipeline execution.';
      }
      return 'No pipeline has been executed yet. Run ' + this.displayCompanyName(company.company_name) + ' to create the first case result and CAM draft.';
    },

    async launchJourneyPreparation() {
      if (!this.onboardId.trim()) return;
      this.journeyStage = 'aggregating';
      this.loading = true;
      this.onboardResult = null;
      try {
        const payload = {
          identifier: this.onboardId.trim(),
          facility_type: this.onboardFacility || 'working_capital',
          amount_requested_cr: this.onboardAmount || 100,
          case_type: this.onboardCaseType || 'NTB',
          purpose: this.onboardPurpose || 'General corporate purpose',
          crilc_available: this.onboardCrilcAvailable,
        };
        if (this.onboardCaseType === 'ETB' && this.etbLookupResult) payload.etb_data = this.etbLookupResult;
        const result = await this.api('onboard', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        this.onboardResult = result;
        this.resolvePreview = result.resolved_from || this.resolvePreview;
        this.pipelineTarget = result.entity_id;
        this.docEntity = result.entity_id;
        this.reportEntity = result.entity_id;
        await this.loadCompanies();
        await this.loadDocumentWorkspace();
        this.journeyStage = 'retrieved';
        this.notify(result.message || 'Verified data retrieved', 'ok');
      } catch {
        this.journeyStage = 'entity';
      } finally {
        this.loading = false;
      }
    },

    proceedToCamBuild() {
      this.journeyStage = 'prebuilt';
    },

    async runJourneyPipeline({ entityId, workingStage, doneStage, doneMessage, errorStage, startProgress }) {
      if (!entityId || this.pipelineRunning) return false;
      this.journeyStage = workingStage;
      this.pipelineTarget = entityId;
      this.pipelineRunning = true;
      this.pipelineError = false;
      this.agentEvents = [];
      this.agentPct = 0;
      this.agentProgress = startProgress;
      this.pipelineDoneResult = null;
      this.camBuildSections = [];

      return await new Promise((resolve, reject) => {
        const es = new EventSource('/api/cases/' + entityId + '/run-stream');
        let settled = false;

        const fail = (message) => {
          if (settled) return;
          settled = true;
          this.pipelineRunning = false;
          this.pipelineError = true;
          this.agentProgress = message || 'Pipeline error';
          es.close();
          this.journeyStage = errorStage;
          this.notify('Pipeline error: ' + (message || 'unknown'), 'error');
          reject(new Error(message || 'Pipeline error'));
        };

        es.onmessage = async (e) => {
          try {
            const evt = JSON.parse(e.data);
            if (evt.type === 'agent_start' || evt.type === 'agent_complete' || evt.type === 'info' || evt.type === 'section_start' || evt.type === 'section_complete') {
              this.agentEvents = [...this.agentEvents, evt];
              if (evt.step && evt.total) {
                this.agentPct = Math.round((evt.step / evt.total) * 100);
                this.agentProgress = evt.title || evt.section || ('Step ' + evt.step + ' / ' + evt.total);
              }
              // Track section build progress for completion cards
              if (evt.type === 'section_start') {
                const idx = this.camBuildSections.findIndex(s => s.id === evt.section);
                if (idx >= 0) {
                  this.camBuildSections[idx].status = 'writing';
                } else {
                  this.camBuildSections = [...this.camBuildSections, { id: evt.section, title: evt.title || evt.section, status: 'writing', step: evt.step, total: evt.total }];
                }
              } else if (evt.type === 'section_complete') {
                const idx = this.camBuildSections.findIndex(s => s.id === evt.section);
                if (idx >= 0) {
                  this.camBuildSections[idx].status = 'done';
                  this.camBuildSections = [...this.camBuildSections];
                } else {
                  this.camBuildSections = [...this.camBuildSections, { id: evt.section, title: evt.title || evt.section, status: 'done', step: evt.step, total: evt.total }];
                }
              }
              return;
            }
            if (evt.type === 'done') {
              if (settled) return;
              settled = true;
              this.pipelineRunning = false;
              this.agentPct = 100;
              this.agentProgress = doneMessage;
              this.pipelineDoneResult = {
                entity_id: entityId,
                recommendation: evt.recommendation,
                risk_grade: evt.risk_grade,
                composite_score: evt.composite_score,
                narrative_mode: evt.narrative_mode,
              };
              es.close();
              try {
                await this.loadCases();
                await this.loadDashboard();
                this.reportEntity = entityId;
                await this.loadCAMReport();
              } catch {}
              this.journeyStage = doneStage;
              this.notify(doneMessage, 'ok');
              resolve(evt);
              return;
            }
            if (evt.type === 'error') {
              fail(evt.message || 'unknown');
            }
          } catch (error) {
            fail(error?.message || 'Invalid pipeline response');
          }
        };

        es.onerror = () => {
          if (settled) return;
          fail('Pipeline connection lost');
        };
      });
    },

    async generateJourneyCam() {
      const entityId = this.journeyEntityId();
      if (!entityId || this.pipelineRunning) return;
      try {
        await this.runJourneyPipeline({
          entityId,
          workingStage: 'drafting',
          doneStage: 'ready',
          doneMessage: 'CAM generated with all uploaded inputs',
          errorStage: 'retrieved',
          startProgress: 'Starting CAM generation',
        });
      } catch {}
    },

    async uploadJourneyFile(category, event, documentRole) {
      const entityId = this.journeyEntityId();
      const files = event?.target?.files;
      if (!entityId || !files || !files.length) return;
      this.loading = true;
      try {
        for (const file of files) {
          const form = new FormData();
          form.append('category', category);
          form.append('file', file);
          if (documentRole) form.append('document_role', documentRole);
          const res = await fetch('/api/companies/' + entityId + '/upload', {
            method: 'POST',
            body: form,
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Upload failed for ' + file.name);
          }
        }
        const names = Array.from(files).map(f => f.name).join(', ');
        this.notify(names + ' uploaded — running OCR extraction...', 'ok');
        try {
          await this.api('companies/' + entityId + '/extract', { method: 'POST' });
          this.notify(names + ' uploaded and extracted', 'ok');
        } catch (exErr) {
          const msg = exErr?.message || exErr?.detail || 'Extraction failed';
          this.notify('Extraction error: ' + msg, 'error');
        }
        this.docEntity = entityId;
        await this.loadDocumentWorkspace();
        await this.loadCases();
        this.pipelineDoneResult = null;
      } catch (e) {
        this.notify(e.message || 'Upload failed', 'error');
      } finally {
        event.target.value = '';
        this.loading = false;
      }
    },

    async deleteJourneyFile(category, filename) {
      const entityId = this.journeyEntityId();
      if (!entityId || !filename) return;
      this.loading = true;
      try {
        const res = await fetch('/api/companies/' + entityId + '/documents/' + encodeURIComponent(category) + '/' + encodeURIComponent(filename), {
          method: 'DELETE',
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Delete failed');
        }
        this.notify(filename + ' removed', 'ok');
        this.docEntity = entityId;
        await this.loadDocumentWorkspace();
        await this.loadCases();
        this.pipelineDoneResult = null;
      } catch (e) {
        this.notify(e.message || 'Delete failed', 'error');
      } finally {
        this.loading = false;
      }
    },



    async openJourneyWorkspace() {
      const entityId = this.journeyEntityId();
      if (!entityId) return;
      this.reportEntity = entityId;
      this.reportTab = 'cam';
      this.navigate('reports');
      await this.loadCAMReport();
    },

    configFieldType(value) {
      if (Array.isArray(value)) return 'list';
      if (value && typeof value === 'object') return 'object';
      if (typeof value === 'boolean') return 'boolean';
      if (typeof value === 'number') return 'number';
      return 'text';
    },

    configFieldValue(value) {
      if (Array.isArray(value)) return value.join(', ');
      if (value == null) return '';
      return String(value);
    },

    applyConfigInput(container, key, rawValue) {
      if (!container || !(key in container)) return;
      const current = container[key];
      if (Array.isArray(current)) {
        const parts = String(rawValue || '')
          .split(',')
          .map(v => v.trim())
          .filter(Boolean);
        const numeric = current.every(v => typeof v === 'number');
        container[key] = numeric
          ? parts.map(v => Number(v)).filter(v => !Number.isNaN(v))
          : parts;
        return;
      }
      if (typeof current === 'number') {
        if (rawValue === '') {
          container[key] = '';
          return;
        }
        const parsed = Number(rawValue);
        if (!Number.isNaN(parsed)) container[key] = parsed;
        return;
      }
      container[key] = rawValue;
    },

    thresholdLabel(index) {
      return ['Lower Band', 'Mid Band', 'Upper Band'][index] || ('Band ' + (index + 1));
    },

    async loadEnums() {
      try { this.enumVals = await this.api('enums'); } catch {}
    },

    /* ─── Smart Onboard ───────────────────────────────────────────── */
    async smartOnboard() {
      if (!this.onboardId.trim()) return;
      this.loading = true;
      this.onboardResult = null;
      try {
        const payload = {
          identifier: this.onboardId.trim(),
          facility_type: this.onboardFacility || 'working_capital',
          amount_requested_cr: this.onboardAmount || 100,
          case_type: this.onboardCaseType || 'NTB',
          purpose: this.onboardPurpose || 'General corporate purpose',
          crilc_available: this.onboardCrilcAvailable,
        };
        if (this.onboardCaseType === 'ETB' && this.etbLookupResult) {
          payload.etb_data = this.etbLookupResult;
        }
        const r = await this.api('onboard', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        this.onboardResult = r;
        this.resolvePreview = r.resolved_from || this.resolvePreview;
        this.notify(r.message || 'Company onboarded successfully', 'ok');
        await this.loadCompanies();
      } catch {} finally { this.loading = false; }
    },

    async previewResolve() {
      if (!this.onboardId.trim()) return;
      this.resolvePreview = null;
      try {
        const r = await this.api('resolve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identifier: this.onboardId.trim() }),
        });
        this.resolvePreview = r;
      } catch {}
    },

    async etbLookup() {
      if (!this.onboardId.trim()) return;
      this.etbLookupResult = null;
      this.etbLookupError = '';
      this.loading = true;
      try {
        // First resolve the identifier to get PAN
        const resolved = await this.api('resolve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identifier: this.onboardId.trim() }),
        });
        if (!resolved || !resolved.pan) {
          this.etbLookupError = 'Could not resolve identifier — no PAN found.';
          return;
        }
        this.resolvePreview = resolved;
        // Fetch CRILC data using PAN to check existing banking relationship
        const crilc = await this.api('external/crilc/' + encodeURIComponent(resolved.pan));
        if (!crilc || !crilc.payload || crilc.payload.aggregate_exposure_cr === 0) {
          this.etbLookupError = 'Not an ETB customer — no existing banking relationship found for this entity.';
          return;
        }
        this.etbLookupResult = {
          entity_name: crilc.payload.entity_name || resolved.company_name,
          pan: resolved.pan,
          cin: resolved.cin,
          aggregate_exposure_cr: crilc.payload.aggregate_exposure_cr,
          fund_based_cr: crilc.payload.fund_based_cr,
          non_fund_based_cr: crilc.payload.non_fund_based_cr,
          total_lenders: crilc.payload.total_lenders,
          classification: crilc.payload.classification,
          sma_status: crilc.payload.sma_status,
        };
        this.notify('ETB data fetched — existing exposure: ' + crilc.payload.aggregate_exposure_cr + ' Cr', 'ok');
      } catch {
        this.etbLookupError = 'Not an ETB customer — no internal conduct data found.';
      } finally { this.loading = false; }
    },

    /* -- navigate to reports/360 for a specific entity -- */
    view360For(entityId) {
      this.reportEntity = entityId;
      this.reportTab = 'view360';
      this.navigate('reports');
      this.$nextTick(() => this.load360());
    },

    /* ─── Documents Page ───────────────────────────────────────────── */
    async loadDocuments() {
      if (!this.docEntity) return;
      this.docLoading = true;
      this.docExtraction = null;
      this.docGaps = null;
      this.docProbe = null;
      const [docs, gaps, extraction, refs] = await Promise.allSettled([
        this.api('companies/' + this.docEntity + '/documents'),
        this.api('companies/' + this.docEntity + '/data-gaps'),
        this.api('companies/' + this.docEntity + '/extraction'),
        this.api('reference-documents?entity_id=' + encodeURIComponent(this.docEntity)),
      ]);
      const probe = await Promise.allSettled([
        this.api('companies/' + this.docEntity + '/probe'),
      ]);

      this.docData = docs.status === 'fulfilled' ? docs.value : null;
      this.docGaps = gaps.status === 'fulfilled' ? gaps.value : null;
      this.docExtraction = extraction.status === 'fulfilled' ? extraction.value : null;
      this.refDocs = refs.status === 'fulfilled' ? (refs.value.groups || {}) : {};
      this.docProbe = probe[0].status === 'fulfilled' ? probe[0].value : null;
      await this.loadDocumentOperations(this.docEntity);
      this.docLoading = false;
    },

    async loadDocumentOperations(entityId) {
      try {
        const path = entityId ? ('companies/' + entityId + '/document-operations') : 'document-operations';
        const result = await this.api(path);
        this.docOpsHistory = (result.operations || []).filter(op => !String(op.operation_type || '').includes('generation'));
      } catch {
        this.docOpsHistory = [];
      }
    },

    async loadDocumentWorkspace() {
      if (!this.docEntity && this.companies.length) this.docEntity = this.companies[0].entity_id;
      await this.loadDocuments();
      if (!this.docOpsHistory.length) await this.loadDocumentOperations();
    },

    async generateDocumentsForWorkspace() {
      if (!this.docEntity) return;
      this.loading = true;
      try {
        const result = await this.api('companies/' + this.docEntity + '/fetch-documents', { method: 'POST' });
        await this.loadDocuments();
        this.notify('Generated ' + (result.files_generated?.length || 0) + ' document artifacts for ' + this.docEntity, 'ok');
      } catch {} finally { this.loading = false; }
    },

    async runExtraction() {
      if (!this.docEntity) return;
      this.docExtracting = true;
      try {
        await this.api('companies/' + this.docEntity + '/extract', { method: 'POST' });
        this.docExtraction = await this.api('companies/' + this.docEntity + '/extraction');
        this.notify('Extraction complete: ' + (this.docExtraction?.document_count || 0) + ' documents processed', 'ok');
      } catch {} finally { this.docExtracting = false; }
    },

    async previewDoc(eid, cat, filename) {
      window.open('/api/companies/' + eid + '/documents/' + cat + '/' + filename, '_blank');
    },

    async uploadWorkspaceFile(event) {
      const file = event?.target?.files?.[0];
      if (!this.docEntity || !file) return;
      this.docUploading = true;
      try {
        const form = new FormData();
        form.append('category', this.docUploadCategory || 'misc');
        form.append('file', file);
        const res = await fetch('/api/companies/' + this.docEntity + '/upload', {
          method: 'POST',
          body: form,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Upload failed');
        }
        this.notify(file.name + ' uploaded — running OCR extraction...', 'ok');
        try {
          await this.api('companies/' + this.docEntity + '/extract', { method: 'POST' });
          this.docExtraction = await this.api('companies/' + this.docEntity + '/extraction');
          this.notify(file.name + ' uploaded and extracted', 'ok');
        } catch (exErr) {
          const msg = exErr?.message || exErr?.detail || 'Extraction failed';
          this.notify('Extraction error: ' + msg, 'error');
        }
        await this.loadDocuments();
        await this.loadCases();
      } catch (e) {
        this.notify(e.message || 'Upload failed', 'error');
      } finally {
        event.target.value = '';
        this.docUploading = false;
      }
    },

    /* ─── Case Detail: Extraction & ETB ────────────────────────────── */
    async runExtractionForDetail() {
      if (!this.detail?.entity_id) return;
      this.loading = true;
      try {
        await this.api('companies/' + this.detail.entity_id + '/extract', { method: 'POST' });
        this.detailExtraction = await this.api('companies/' + this.detail.entity_id + '/extraction');
        this.notify('Extraction complete', 'ok');
      } catch {} finally { this.loading = false; }
    },

    async runETBForDetail() {
      if (!this.detail?.entity_id) return;
      this.loading = true;
      try {
        // Ensure extraction is done first
        if (!this.detailExtraction) {
          await this.api('companies/' + this.detail.entity_id + '/extract', { method: 'POST' });
          this.detailExtraction = await this.api('companies/' + this.detail.entity_id + '/extraction');
        }
        await this.api('companies/' + this.detail.entity_id + '/etb-analytics', { method: 'POST' });
        this.detailETB = await this.api('companies/' + this.detail.entity_id + '/etb-analytics');
        this.notify('ETB analysis complete', 'ok');
      } catch {} finally { this.loading = false; }
    },

    /* ─── Report Entity Change Event ─────────────────────────────── */
    async onReportEntityChange() {
      this.camHtml = '';
      this.camSections = [];
      this.camActiveSection = 0;
      this.camComments = {};
      this.camCommentDrafts = {};
      this.camCommentSaving = false;
      this.memoHtml = '';
      this.view360Data = null;
      this.chatMessages = [];
      this.reportProbe = null;
      await this.loadReportProbe();
      if (this.reportTab === 'chat') await this.loadChatHistory();
    },

    /* ─── CAM Report Viewer ───────────────────────────────────────── */
    async loadCAMReport() {
      if (!this.reportEntity) return;
      this.loading = true;
      try {
        await this.loadReportProbe();
        // Fetch raw markdown for sectioned navigation
        const mdRes = await fetch('/api/cases/' + this.reportEntity + '/cam');
        if (!mdRes.ok) throw new Error('Failed to load CAM report');
        const mdData = await mdRes.json();
        const rawMd = mdData.cam_text || '';
        await this.loadCAMComments();

        // Parse markdown into sections — split on H2 headings (## )
        const parts = rawMd.split(/(?=\n## )/);
        if (parts.length > 1) {
          this.camSections = parts.map((part, idx) => {
            const trimmed = part.replace(/^\n/, '');
            const firstNL = trimmed.indexOf('\n');
            const heading = firstNL > 0 ? trimmed.slice(0, firstNL) : trimmed;
            const title = heading.replace(/^#+\s*/, '').trim() || ('Section ' + (idx + 1));
            return { id: idx, key: this.camSectionKey(title), title, html: this.renderMd(trimmed) };
          })
          // Drop cover/TOC fragments so the report nav stays focused on substantive CAM sections.
          .filter((s) => /^(\d+[a-z]?\.|annexure|appendix|disclaimer)/i.test(s.title));
          this.camActiveSection = 0;
          this.camHtml = '';
          await this.loadCamSectionEdits();
        } else {
          // Fallback: no section headings found, use HTML iframe
          this.camSections = [];
          const htmlRes = await fetch('/api/cases/' + this.reportEntity + '/cam-html');
          if (!htmlRes.ok) throw new Error('Failed to load CAM HTML');
          this.camHtml = await htmlRes.text();
        }
      } catch(e) {
        this.notify(e.message, 'error');
      } finally { this.loading = false; }
    },

    camSectionKey(title) {
      return (title || '').replace(/\s+/g, ' ').trim();
    },

    async loadCAMComments() {
      if (!this.reportEntity) {
        this.camComments = {};
        this.camCommentDrafts = {};
        return;
      }
      const r = await this.api('cases/' + this.reportEntity + '/comments');
      this.camComments = r.comments || {};
      this.camCommentDrafts = { ...this.camComments };
    },

    async saveCamComment() {
      const section = this.camSections[this.camActiveSection];
      if (!section || !this.reportEntity) return;
      this.camCommentSaving = true;
      try {
        const comments = { ...this.camComments };
        const value = (this.camCommentDrafts[section.key] || '').trim();
        if (value) comments[section.key] = value;
        else delete comments[section.key];
        const r = await this.api('cases/' + this.reportEntity + '/comments', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ comments }),
        });
        this.camComments = r.comments || comments;
        this.camCommentDrafts = { ...this.camCommentDrafts, [section.key]: this.camComments[section.key] || '' };
        this.notify('Section comment saved', 'ok');
      } catch {} finally { this.camCommentSaving = false; }
    },

    resetCamComment() {
      const section = this.camSections[this.camActiveSection];
      if (!section) return;
      this.camCommentDrafts = {
        ...this.camCommentDrafts,
        [section.key]: this.camComments[section.key] || '',
      };
    },

    toggleCamEditMode() {
      this.camEditMode = !this.camEditMode;
    },

    async loadCamSectionEdits() {
      if (!this.reportEntity) return;
      try {
        const r = await this.api('cases/' + this.reportEntity + '/cam-section-edits');
        this.camSectionEdits = r.edits || {};
        // Apply saved edits to section HTML
        for (const sec of this.camSections) {
          if (this.camSectionEdits[sec.key]) {
            sec.editedHtml = this.camSectionEdits[sec.key].html;
            sec.editedBy = this.camSectionEdits[sec.key].edited_by;
            sec.editedAt = this.camSectionEdits[sec.key].updated_at;
          }
        }
      } catch {}
    },

    async saveCamSectionEdit() {
      const section = this.camSections[this.camActiveSection];
      if (!section || !this.reportEntity) return;
      this.camEditSaving = true;
      try {
        const el = document.getElementById('cam-edit-area');
        if (!el) return;
        const editedHtml = el.innerHTML;
        const r = await this.api('cases/' + this.reportEntity + '/cam-section-edits', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ section_key: section.key, edited_html: editedHtml }),
        });
        this.camSectionEdits = r.edits || {};
        section.editedHtml = editedHtml;
        section.editedBy = 'RM';
        section.editedAt = new Date().toISOString();
        this.notify('Section edit saved', 'ok');
      } catch(e) {
        this.notify('Failed to save edit: ' + e.message, 'error');
      } finally { this.camEditSaving = false; }
    },

    revertCamSectionEdit() {
      const section = this.camSections[this.camActiveSection];
      if (!section) return;
      section.editedHtml = null;
      section.editedBy = null;
      section.editedAt = null;
      // Also delete from server
      if (this.reportEntity) {
        this.api('cases/' + this.reportEntity + '/cam-section-edits', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ section_key: section.key, edited_html: '' }),
        }).then(r => {
          this.camSectionEdits = r.edits || {};
          this.notify('Section reverted to original', 'ok');
        }).catch(() => {});
      }
    },

    async downloadCAMPdf() {
      if (!this.reportEntity) return;
      const section = this.camSections[this.camActiveSection];
      if (section) {
        const draft = (this.camCommentDrafts[section.key] || '').trim();
        const saved = this.camComments[section.key] || '';
        if (draft !== saved) await this.saveCamComment();
      }
      window.open('/api/cases/' + this.reportEntity + '/cam-pdf', '_blank');
    },

    openCamNewTab() {
      if (!this.reportEntity) return;
      window.open('/api/cases/' + this.reportEntity + '/cam-html', '_blank');
    },

    /* ─── One-Page Memo ────────────────────────────────────────────── */
    async loadOnePager() {
      if (!this.reportEntity) return;
      this.loading = true;
      try {
        const r = await fetch('/api/cases/' + this.reportEntity + '/one-pager');
        if (!r.ok) throw new Error('Failed to load one-page memo');
        this.memoHtml = await r.text();
      } catch(e) {
        this.notify(e.message, 'error');
      } finally { this.loading = false; }
    },

    openMemoNewTab() {
      if (!this.reportEntity) return;
      window.open('/api/cases/' + this.reportEntity + '/one-pager', '_blank');
    },

    /* ─── Analyst Chat ─────────────────────────────────────────────── */
    async loadChatHistory() {
      if (!this.reportEntity) { this.chatMessages = []; return; }
      try {
        await this.loadReportProbe();
        const r = await this.api('chat/' + this.reportEntity + '/history');
        this.chatMessages = r.messages || [];
        this.$nextTick(() => this.scrollChat());
      } catch { this.chatMessages = []; }
    },

    async sendChat() {
      if (!this.reportEntity || !this.chatInput.trim()) return;
      const msg = this.chatInput.trim();
      this.chatInput = '';
      this.chatMessages.push({ role: 'user', content: msg });
      this.chatLoading = true;
      this.$nextTick(() => this.scrollChat());
      try {
        const r = await this.api('chat/' + this.reportEntity, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg }),
        });
        this.chatMessages.push({ role: 'assistant', content: r.response });
      } catch(e) {
        this.chatMessages.push({ role: 'assistant', content: 'Error: ' + e.message });
      } finally {
        this.chatLoading = false;
        this.$nextTick(() => this.scrollChat());
      }
    },

    chatQuick(msg) {
      this.chatInput = msg;
      this.sendChat();
    },

    async clearChat() {
      if (!this.reportEntity) return;
      try {
        await this.api('chat/' + this.reportEntity, { method: 'DELETE' });
        this.chatMessages = [];
        this.notify('Chat cleared', 'ok');
      } catch {}
    },

    scrollChat() {
      const el = document.getElementById('chatMessages');
      if (el) el.scrollTop = el.scrollHeight;
    },

    /* ─── ETB Analytics Page ───────────────────────────────────────── */
    async runETBAnalytics() {
      if (!this.etbEntity) return;
      this.loading = true;
      this.etbData = null;
      try {
        // Ensure extraction is done
        try { await this.api('companies/' + this.etbEntity + '/extract', { method: 'POST' }); } catch {}
        const r = await this.api('companies/' + this.etbEntity + '/etb-analytics', { method: 'POST' });
        this.etbData = await this.api('companies/' + this.etbEntity + '/etb-analytics');
        this.etbTab = 'summary';
        this.notify('ETB analysis: ' + (this.etbData?.risk_grade || 'N/A'), 'ok');
      } catch(e) {
        this.notify('ETB analytics failed — entity may not have conduct data', 'error');
      } finally { this.loading = false; }
    },

    /* ─── Fraud Detection Page ─────────────────────────────────────── */
    async runFraudAnalysis() {
      if (!this.fraudEntity) return;
      this.loading = true;
      this.fraudData = null;
      try {
        const r = await this.api('companies/' + this.fraudEntity + '/fraud-analysis', { method: 'POST' });
        this.fraudData = r;
        this.fraudTab = 'summary';
        this.notify('Fraud scan: ' + (r?.risk_grade || 'N/A') + ' (' + (r?.composite_score?.toFixed(1) || '0') + ')', 'ok');
      } catch(e) {
        this.notify('Fraud analysis failed: ' + (e.message||'unknown'), 'error');
      } finally { this.loading = false; }
    },

    /* ─── 360° View ────────────────────────────────────────────────── */
    async load360() {
      if (!this.reportEntity) return;
      this.loading = true;
      this.view360Data = null;
      try {
        this.view360Data = await this.api('companies/' + this.reportEntity + '/360');
        this.v360tab = 'overview';
      } catch {} finally { this.loading = false; }
    },

    async submitCompany() {
      const co = this.newCo;
      if (!co.entity_id || !co.company_name || !co.sector || !co.amount_requested_cr) {
        this.notify('Please fill all required fields (Entity ID, Name, Sector, Amount)', 'error');
        return;
      }
      // Clean line_items: remove null/zero
      const lineItems = {};
      for (const [k, v] of Object.entries(co.line_items)) {
        if (v != null && v !== 0) lineItems[k] = v;
      }
      const payload = {
        entity_id: co.entity_id,
        company_name: co.company_name,
        cin: co.cin || undefined,
        pan: co.pan || undefined,
        sector: co.sector,
        borrower_type: co.borrower_type,
        date_of_incorporation: co.date_of_incorporation || undefined,
        credit_rating: co.credit_rating || undefined,
        rating_agency: co.rating_agency || undefined,
        employee_count: co.employee_count || undefined,
        case_type: co.case_type,
        facility_type: co.facility_type,
        amount_requested_cr: co.amount_requested_cr,
        purpose: co.purpose || undefined,
        tenor_months: co.tenor_months || undefined,
        existing_limit_cr: co.existing_limit_cr || undefined,
        line_items: lineItems,
      };
      // Add collateral if provided
      if (co.collateral_type && co.collateral_market_value) {
        payload.collateral = [{
          collateral_type: co.collateral_type,
          description: co.collateral_desc,
          market_value_cr: co.collateral_market_value,
          forced_sale_value_cr: co.collateral_fsv || co.collateral_market_value * 0.7,
        }];
      }

      this.loading = true;
      try {
        const r = await this.api('companies', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        this.notify(r.message || 'Company added', 'ok');
        this.resetCompanyForm();
        await this.loadCompanies();
        this.navigate('pipeline');
      } catch {} finally { this.loading = false; }
    },

    resetCompanyForm() {
      this.newCo = {
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
      };
    },

    /* ─── Downloads ────────────────────────────────────────────────── */
    downloadCAM() {
      if (!this.detail?.cam_text) return;
      this._download(this.detail.entity_id + '_CAM.md', this.detail.cam_text, 'text/markdown');
    },

    downloadJSON() {
      if (!this.detail?.fact_pack) return;
      this._download(this.detail.entity_id + '_factpack.json',
                     JSON.stringify(this.detail.fact_pack, null, 2), 'application/json');
    },

    _download(name, content, mime) {
      const blob = new Blob([content], { type: mime });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = name;
      a.click();
      URL.revokeObjectURL(a.href);
    },

    /* ─── Formatters ───────────────────────────────────────────────── */
    gradeCls(g) {
      if (!g) return '';
      if (g === 'A') return 'badge-green';
      if (g === 'B') return 'badge-blue';
      if (g === 'C') return 'badge-amber';
      return 'badge-red';
    },

    recCls(r) {
      if (!r) return '';
      if (r === 'approve') return 'badge-green';
      if (r === 'conditional_approve') return 'badge-blue';
      if (r === 'refer') return 'badge-amber';
      if (r === 'decline') return 'badge-red';
      return '';
    },

    sevCls(s) {
      if (s === 'critical') return 'badge-red';
      if (s === 'high') return 'badge-amber';
      if (s === 'medium') return 'badge-blue';
      return 'badge-info';
    },

    scoreCls(s) {
      if (s >= 65) return 'score-good';
      if (s >= 50) return 'score-ok';
      return 'score-bad';
    },

    fmtRec(r) {
      if (!r) return '';
      return this.humanizeText(r);
    },

    fmtTime(t) {
      if (!t) return '';
      try {
        const d = new Date(t);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } catch { return t; }
    },

    /* ─── Markdown Renderer ────────────────────────────────────────── */
    renderMd(text) {
      if (!text) return '';
      let h = this._escHtml(text);

      /* Tables  —  | col | col | */
      h = h.replace(/((?:^\|.+\|$\n?)+)/gm, (block) => {
        const rows = block.trim().split('\n').filter(r => r.trim());
        if (rows.length < 2) return block;
        let tbl = '<table>';
        rows.forEach((row, i) => {
          // skip separator row  |---|
          if (/^\|[\s\-:|]+\|$/.test(row)) return;
          const cells = row.split('|').slice(1, -1);
          const tag = i === 0 ? 'th' : 'td';
          tbl += '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
        });
        tbl += '</table>';
        return tbl;
      });

      /* Headings */
      h = h.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
      h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
      h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
      h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>');

      /* Bold / italic */
      h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');

      /* Horizontal rule */
      h = h.replace(/^---+$/gm, '<hr>');

      /* Bullet lists */
      h = h.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
      h = h.replace(/((?:<li>.+<\/li>\n?)+)/g, '<ul>$1</ul>');

      /* Numbered lists */
      h = h.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

      /* Paragraphs */
      h = h.replace(/\n{2,}/g, '</p><p>');
      h = '<p>' + h + '</p>';
      h = h.replace(/<p>\s*<(h[1-4]|table|ul|ol|hr|li)/g, '<$1');
      h = h.replace(/<\/(h[1-4]|table|ul|ol|hr|li)>\s*<\/p>/g, '</$1>');
      return h;
    },

    _escHtml(s) {
      return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    },
  };
}
