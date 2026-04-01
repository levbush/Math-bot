function typeset(el) {
  if (!window.MathJax) return;
  const ready = MathJax.startup?.promise ?? Promise.resolve();
  ready.then(() => MathJax.typesetPromise([el])).catch(() => {});
}

function renderMarkdown(el, text) {
  text = text.replace(/(\$\$[\s\S]*?\$\$)/g, '\n\n$1\n\n');
  const encoded = text.replace(/\$\$[\s\S]*?\$\$|\$[^$\n]*?\$/g, m => {
    return '\x00' + btoa(unescape(encodeURIComponent(m))) + '\x00';
  });
  let html = marked.parse(encoded, { breaks: true });
  html = html.replace(/\x00([A-Za-z0-9+/=]+)\x00/g, (_, b64) => {
    return decodeURIComponent(escape(atob(b64)));
  });
  el.innerHTML = html;
  typeset(el);
}

const problemEl = document.getElementById('problem-text');
if (problemEl) renderMarkdown(problemEl, problemEl.dataset.raw);

const buttons = document.querySelectorAll('.btn-ai');
const panel = document.getElementById('ai-panel');
const label = document.getElementById('ai-label');
const responseEl = document.getElementById('ai-response');
const confirmBtn = document.getElementById('confirm-btn');

const modeLabels = { 
  check: 'answer check', 
  hint: 'hint', 
  steps: 'step-by-step', 
  explain: 'explanation' 
};

console.log('Found buttons:', buttons.length);

buttons.forEach(btn => {
  btn.addEventListener('click', async () => {
    const mode = btn.dataset.mode;
    const answer = document.getElementById('answer').value.trim();
    
    console.log('Button clicked:', mode, 'Answer length:', answer.length);

    buttons.forEach(b => { b.disabled = true; b.classList.remove('active'); });
    btn.classList.add('active');
    if (panel) panel.style.display = 'block';
    if (label) label.textContent = modeLabels[mode];
    if (responseEl) {
      responseEl.className = 'ai-response';
      responseEl.innerHTML = '<span class="ai-cursor"></span>';
    }

    const body = new FormData();
    body.append('mode', mode);
    body.append('answer', answer);

    try {
      const res = await fetch('/problem/ai', { method: 'POST', body });
      const data = await res.json();
      
      console.log('Response:', res.status, data);

      if (res.status === 429) {
        const mins = Math.ceil(data.wait / 60);
        if (panel) panel.style.display = 'none';
        if (typeof showToast === 'function') {
          showToast(`Too many requests - please wait ${mins} minute${mins !== 1 ? 's' : ''} before asking again.`);
        }
        return;
      }

      if (!res.ok || data.error) {
        if (responseEl) responseEl.textContent = data.error || 'Request failed.';
        return;
      }

      if (mode === 'check') {
        if (responseEl) renderMarkdown(responseEl, data.text);
        if (data.verdict === 'CORRECT') {
          if (responseEl) responseEl.classList.add('check-correct');
          if (confirmBtn) { confirmBtn.disabled = false; confirmBtn.title = ''; }
        } else if (data.verdict === 'INCORRECT') {
          if (responseEl) responseEl.classList.add('check-wrong');
        }
      } else {
        if (responseEl) renderMarkdown(responseEl, data.text);
      }

    } catch (e) {
      console.error('Error:', e);
      if (responseEl) responseEl.textContent = 'Request failed: ' + e.message;
    } finally {
      buttons.forEach(b => { b.disabled = false; });
      btn.classList.remove('active');
    }
  });
});
