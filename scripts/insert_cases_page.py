"""One-time script to insert the Cases page section into index.html"""
import re

with open(r'src/ui/templates/index.html', encoding='utf-8') as f:
    content = f.read()

cases_section = '''
    <!-- --- CASES ----------------------------------------------------------------- -->
    <section x-show="page==='cases'" x-cloak>
      <div class="page-header">
        <h1>Cases</h1>
        <button class="btn btn-primary" @click="navigate('onboard')">&#43; New Case</button>
      </div>

      <div class="card">
        <table class="data-table" x-show="companies.length">
          <thead><tr>
            <th>ID</th><th>Company</th><th>Sector</th><th>Type</th>
            <th>Amount (Cr)</th><th>Status</th><th>Grade</th><th>Actions</th>
          </tr></thead>
          <tbody>
            <template x-for="c in companies" :key="c.entity_id">
              <tr>
                <td><span class="badge badge-info" x-text="c.entity_id"></span></td>
                <td x-text="c.company_name"></td>
                <td x-text="c.sector"></td>
                <td x-text="c.case_type?.toUpperCase()"></td>
                <td x-text="c.requested_amount_cr?.toFixed(0) || '-'"></td>
                <td>
                  <span class="badge" :class="caseMap[c.entity_id] ? 'badge-green' : 'badge-amber'"
                        x-text="caseMap[c.entity_id] ? 'Analysed' : 'Pending'"></span>
                </td>
                <td>
                  <span x-show="caseMap[c.entity_id]" class="badge"
                        :class="gradeCls(caseMap[c.entity_id]?.risk_grade)"
                        x-text="caseMap[c.entity_id]?.risk_grade || ''"></span>
                  <span x-show="!caseMap[c.entity_id]">&#8212;</span>
                </td>
                <td class="action-cell">
                  <button class="btn btn-sm btn-primary" @click="viewCase(c.entity_id)"
                          x-text="caseMap[c.entity_id] ? 'View' : 'Open'"></button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <p class="empty-state" x-show="!companies.length">
          No cases found. Use <a href="#" @click.prevent="navigate('onboard')">Smart Onboard</a> to add a company.
        </p>
      </div>
    </section>

'''

insert_before = "<section x-show=\"page==='detail'\" x-cloak>"
idx = content.find(insert_before)
if idx == -1:
    print("ERROR: Could not find insertion point!")
else:
    print(f"Inserting at index {idx}")
    new_content = content[:idx] + cases_section + content[idx:]
    with open(r'src/ui/templates/index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Done!")
