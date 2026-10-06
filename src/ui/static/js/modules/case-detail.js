/* CAM Intelligence Platform — Case detail: summary tabs, extraction, ETB, risk checks, run history, downloads.
   Merged into the Alpine component by camApp() in app.js; `this` is that component. */

function camCaseDetail() {
  return {
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
        this.detailFraud = null;
        this.detailPep = null;
        this.detailRuns = [];
        try { this.detailExtraction = await this.api('companies/' + eid + '/extraction'); } catch {}
        if (String(this.detail?.case_type || '').toUpperCase() === 'ETB') {
          try { this.detailETB = await this.api('companies/' + eid + '/etb-analytics', undefined, { quiet: true }); } catch {}
        }
        try { this.detailDocs = await this.api('companies/' + eid + '/documents'); } catch {}
      } catch {
        this.notify('Run the pipeline for this company first', 'error');
      } finally { this.loading = false; }
    },

    /* ─── Case Detail: Risk checks & run history ───────────────────── */
    async loadRiskChecks() {
      const eid = this.detail?.entity_id;
      if (!eid) return;
      // A stored fraud scan is optional (404 until the first run); PEP screening is computed on request.
      try { this.detailFraud = await this.api('companies/' + eid + '/fraud-analysis', undefined, { quiet: true }); }
      catch { this.detailFraud = null; }
      try { this.detailPep = await this.api('companies/' + eid + '/pep-screening'); }
      catch { this.detailPep = null; }
    },

    async runFraudForDetail() {
      const eid = this.detail?.entity_id;
      if (!eid) return;
      this.loading = true;
      try {
        this.detailFraud = await this.api('companies/' + eid + '/fraud-analysis', { method: 'POST' });
        this.notify('Fraud scan: ' + (this.detailFraud?.risk_grade || 'N/A'), 'ok');
      } catch {} finally { this.loading = false; }
    },

    async loadRunHistory() {
      const eid = this.detail?.entity_id;
      if (!eid) return;
      try { this.detailRuns = (await this.api('cases/' + eid + '/runs')).runs || []; }
      catch { this.detailRuns = []; }
    },

    async generateDocumentsForDetail() {
      if (!this.detail?.entity_id) return;
      this.loading = true;
      try {
        const result = await this.api('companies/' + this.detail.entity_id + '/fetch-documents', { method: 'POST' });
        this.detailDocs = await this.api('companies/' + this.detail.entity_id + '/documents');
        if (this.docEntity === this.detail.entity_id) await this.loadDocumentOperations(this.detail.entity_id);
        await this.loadCases();
        this.notify('Generated ' + (result.files_generated?.length || 0) + ' document artifacts for ' + this.detail.entity_id, 'ok');
      } catch {} finally { this.loading = false; }
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
  };
}
