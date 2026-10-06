/* CAM Intelligence Platform — Pipeline page: agent list, streamed runs (GET /api/cases/{id}/run-stream), run-all.
   Merged into the Alpine component by camApp() in app.js; `this` is that component. */

function camPipeline() {
  return {
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
            if (evt.type === 'agent_complete' && evt.total) {
              // Agents can finish out of order when they run in parallel; `completed` is the true count.
              const done = evt.completed ?? evt.step;
              this.agentProgress = done + ' / ' + evt.total + ' agents done — ' + this.humanizeText(evt.agent);
              this.agentPct = Math.round((done / evt.total) * 100);
            } else if (evt.type === 'agent_start') {
              this.agentProgress = 'Running ' + this.humanizeText(evt.agent);
            }
          } else if (evt.type === 'section_start' || evt.type === 'section_complete') {
            this.agentEvents = [...this.agentEvents, evt];
            if (evt.type === 'section_complete' && evt.total) {
              this.agentProgress = 'Narrative: ' + (evt.completed ?? evt.step) + ' / ' + evt.total
                + ' sections written — ' + (evt.title || evt.section);
            } else if (evt.type === 'section_start') {
              this.agentProgress = 'Narrative: writing ' + (evt.title || evt.section);
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
        const total = r.results?.length || 0;
        if (r.failed) {
          const names = r.results.filter(x => x.error).map(x => x.entity_id).join(', ');
          this.notify((total - r.failed) + ' of ' + total + ' processed; failed: ' + names, 'error');
        } else {
          this.notify('All ' + total + ' companies processed', 'ok');
        }
        await this.loadCases();
        await this.loadDashboard();
      } catch {} finally { this.loading = false; }
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

    selectedPipelineCase() {
      return this.caseMap[this.pipelineTarget] || null;
    },

    pipelineEmptyStateMessage() {
      const company = this.selectedCompany();
      if (!company) {
        return 'No borrower selected. Choose a borrower to start the first pipeline execution.';
      }
      return 'No pipeline has been executed yet. Run ' + this.displayCompanyName(company.company_name) + ' to create the first case result and CAM draft.';
    },
  };
}
