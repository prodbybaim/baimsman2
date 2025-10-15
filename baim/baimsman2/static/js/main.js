(function(){
  const body = document.body;
  function setTheme(t){ if(t==='dark') body.classList.add('dark'); else body.classList.remove('dark'); localStorage.setItem('site-theme', t); }
  const saved = localStorage.getItem('site-theme') || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(saved);
  window.toggleTheme = function(){ const now = body.classList.contains('dark') ? 'light' : 'dark'; setTheme(now); }

  const settingsBtn = document.getElementById('settingsBtn');
  const panel = document.createElement('div');
  panel.className = 'settings-panel';
  panel.innerHTML = `<div style="font-weight:700;margin-bottom:8px">Settings</div>
    <div class="switch"><div>Theme</div><button id="themeToggle" class="cta small">Toggle</button></div>
    <div style="margin-top:10px" class="small">Page transitions enabled</div>`;
  document.body.appendChild(panel);
  settingsBtn.addEventListener('click', ()=> panel.classList.toggle('open'));
  document.getElementById('themeToggle').addEventListener('click', ()=> window.toggleTheme());

  // page overlay
  const overlay = document.createElement('div');
  overlay.className = 'page-overlay';
  overlay.innerHTML = '<div class="loader"></div>';
  document.body.appendChild(overlay);
  function showOverlay(){ overlay.classList.add('show'); }
  function hideOverlay(){ overlay.classList.remove('show'); }

  // intercept links for internal pages
  document.addEventListener('click', function(e){
    const a = e.target.closest('a');
    if(!a) return;
    const href = a.getAttribute('href');
    if(!href) return;
    if(href.startsWith('http') || href.startsWith('mailto:') || href.startsWith('#')) return;
    if(e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    showOverlay();
    setTimeout(()=>{ window.location.href = href; }, 380);
  }, true);

  window.addEventListener('load', ()=>{ setTimeout(()=>{ document.querySelectorAll('.page-overlay').forEach(el=>el.classList.remove('show')); }, 200); });
})();