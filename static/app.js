const input = document.querySelector('#answerInput');
const button = document.querySelector('#analyzeButton');
const count = document.querySelector('#charCount');
const status = document.querySelector('#integrationStatus');
const emptyState = document.querySelector('#emptyState');
const report = document.querySelector('#report');
const template = document.querySelector('#claimTemplate');

input.addEventListener('input', () => { count.textContent = `${input.value.length.toLocaleString()} / 12,000`; });
fetch('/api/health').then(r => r.json()).then(h => {
  status.textContent = h.tavily_configured ? `TAVILY LIVE · ${h.bifrost_configured ? 'BIFROST MODEL' : 'LOCAL EXTRACTOR'}` : 'DEMO SEARCH · ADD TAVILY KEY';
  status.style.color = h.tavily_configured ? '#8ef0c2' : '#f2bd6c';
}).catch(() => { status.textContent = 'LOCAL DEMO'; });

button.addEventListener('click', async () => {
  const answer = input.value.trim();
  if (!answer) { input.focus(); return; }
  button.disabled = true;
  button.querySelector('.button-label').textContent = 'Tracing…';
  button.querySelector('.button-arrow').textContent = '◌';
  document.querySelector('#reportTag').textContent = 'ANALYZING';
  try {
    const response = await fetch('/api/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({answer})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Analysis could not be completed.');
    render(data);
  } catch (error) {
    document.querySelector('#reportTag').textContent = 'CHECK INPUT';
    emptyState.classList.remove('hidden'); report.classList.add('hidden');
    emptyState.querySelector('h3').textContent = 'Could not finish analysis';
    emptyState.querySelector('p').textContent = error.message;
  } finally {
    button.disabled = false;
    button.querySelector('.button-label').textContent = 'Trace claims';
    button.querySelector('.button-arrow').textContent = '↗';
  }
});

function render(data) {
  emptyState.classList.add('hidden'); report.classList.remove('hidden');
  document.querySelector('#reportTag').textContent = data.search_mode === 'tavily' ? 'LIVE SEARCH' : 'DEMO MODE';
  document.querySelector('#claimCount').textContent = data.claim_count;
  document.querySelector('#analysisMeta').textContent = `${data.mode.toUpperCase()} EXTRACTOR · ${new Date(data.analyzed_at).toLocaleString()}`;
  document.querySelector('#scoreValue').textContent = data.overall_score == null ? '—' : data.overall_score;
  const ring = document.querySelector('#scoreRing');
  ring.style.background = data.overall_score == null ? 'conic-gradient(#687582 0deg,#1e2d32 0deg)' : `conic-gradient(var(--mint) ${Math.round(data.overall_score*3.6)}deg,#1e2d32 0deg)`;
  document.querySelector('#scoreLabel').textContent = data.overall_score == null ? 'Demo evidence only' : data.overall_score >= 75 ? 'Strong freshness signal' : data.overall_score >= 50 ? 'Review before relying' : 'Potential staleness detected';
  document.querySelector('#scoreDescription').textContent = data.overall_score == null ? 'Connect Tavily for live claim evidence and a freshness score.' : 'A triage score across evidence match and available source dates. Verify important claims yourself.';
  const list = document.querySelector('#claimList'); list.replaceChildren();
  data.claims.forEach((claim, i) => {
    const card = template.content.firstElementChild.cloneNode(true);
    card.querySelector('.claim-index').textContent = `CLAIM ${String(i+1).padStart(2,'0')} · ${claim.freshness_score}/100 · ${claim.freshness_label.toUpperCase()}`;
    const pill = card.querySelector('.status-pill');
    const labels = {supported:'Likely relevant',review:'Needs review',unsupported:'No evidence',demo:'Demo only'};
    pill.textContent = labels[claim.status] || 'Needs review'; pill.classList.add(claim.status);
    card.querySelector('.claim-text').textContent = claim.text;
    card.querySelector('.claim-rationale').textContent = claim.rationale;
    const sources = card.querySelector('.source-list');
    claim.sources.forEach(source => {
      const row = document.createElement('div'); row.className='source';
      const link = document.createElement('a'); link.href=source.url; link.target='_blank'; link.rel='noopener noreferrer'; link.textContent=source.title; row.append(link);
      const excerpt = document.createElement('div'); excerpt.className='source-excerpt'; excerpt.textContent=source.content; row.append(excerpt);
      const meta = document.createElement('div'); meta.className='source-meta'; meta.textContent=`SOURCE DATE · ${source.published_date || 'UNAVAILABLE'}  /  ${source.age_label || 'Date unavailable'}`; row.append(meta);
      sources.append(row);
    });
    list.append(card);
  });
}

