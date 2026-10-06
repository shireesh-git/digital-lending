/* CAM Intelligence Platform — Dashboard metrics, charts and approval-status counts (GET /api/dashboard).
   Merged into the Alpine component by camApp() in app.js; `this` is that component. */

function camDashboard() {
  return {
    /* ─── Dashboard ────────────────────────────────────────────────── */
    async loadDashboard() {
      this.dash = await this.api('dashboard');
      this.$nextTick(() => this.drawCharts());
    },

    drawCharts() {
      if (typeof Chart === 'undefined') return;
      const css = getComputedStyle(document.documentElement);
      const textColor = css.getPropertyValue('--text-sec').trim() || '#555';
      const gridColor = css.getPropertyValue('--border').trim() || '#ddd';

      /* Grade distribution (GET /api/dashboard → grade_distribution) */
      const gd = this.dash.grade_distribution || {};
      const grades = ['A', 'B', 'C', 'D', 'E', ...Object.keys(gd).filter(g => !'ABCDE'.includes(g))];
      const gColors = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#991b1b', '#9ca3af'];
      const gCtx = document.getElementById('gradeChart');
      if (gCtx) {
        if (this._gradeChart) this._gradeChart.destroy();
        this._gradeChart = new Chart(gCtx, {
          type: 'doughnut',
          data: {
            labels: grades.map(g => 'Grade ' + g),
            datasets: [{ data: grades.map(g => gd[g] || 0), backgroundColor: gColors, borderWidth: 0 }],
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { color: textColor, font: { size: 12 } } } },
          },
        });
      }

      /* Score breakdown of the most recent case (GET /api/cases summary scores) */
      const recent = (this.dash.recent_cases || [])[0];
      const latest = recent ? this.caseMap[recent.entity_id] : null;
      const sCtx = document.getElementById('scoreChart');
      if (sCtx && latest) {
        if (this._scoreChart) this._scoreChart.destroy();
        this._scoreChart = new Chart(sCtx, {
          type: 'bar',
          data: {
            labels: ['Financial', 'Conduct', 'Governance', 'Market', 'Composite'],
            datasets: [{
              data: [latest.financial_score, latest.conduct_score,
                     latest.governance_score, latest.market_score, latest.composite_score],
              backgroundColor: ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#10b981'],
              borderRadius: 4,
            }],
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            indexAxis: 'y',
            scales: {
              x: { min: 0, max: 100, ticks: { color: textColor }, grid: { color: gridColor } },
              y: { ticks: { color: textColor }, grid: { display: false } },
            },
            plugins: { legend: { display: false } },
          },
        });
      }
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
        subtitle: this.titleCase(this.caseMap[company.entity_id]?.facility_type || company.facility_type || 'Facility not set') + ' • ' + this.formatCurrencyCr(company.requested_amount_cr || 0),
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
        const exception = detail.exception_count
          ? (detail.top_exception || 'Validation exception flagged')
            + (detail.exception_count > 1 ? ' (+' + (detail.exception_count - 1) + ' more)' : '')
          : 'Grade ' + grade + ' — credit risk requires closer review';
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

    /* Approval workflow counts from GET /api/dashboard (human decisions on the latest runs). */
    workflowStatusRows() {
      const order = ['draft', 'submitted', 'returned_for_rework', 'approved', 'rejected'];
      const counts = this.dash.workflow_status || {};
      return Object.keys(counts)
        .sort((a, b) => order.indexOf(a) - order.indexOf(b))
        .map(status => ({ status, count: counts[status] }));
    },

    workflowStatusClass(status) {
      if (status === 'approved') return 'badge-green';
      if (status === 'rejected') return 'badge-red';
      if (status === 'submitted') return 'badge-blue';
      if (status === 'returned_for_rework') return 'badge-amber';
      return 'badge-grey';
    },

    latestCaseLabel() {
      const latest = (this.dash.recent_cases || [])[0];
      return latest ? 'Score Breakdown — ' + this.displayCompanyName(latest.company_name) : 'Score Breakdown';
    },
  };
}
