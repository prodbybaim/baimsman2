// Theme toggle & settings
(function(){
  const body = document.body;
  function setTheme(t){ if(t==='dark') body.classList.add('dark'); else body.classList.remove('dark'); localStorage.setItem('site-theme', t); }
  const saved = localStorage.getItem('site-theme') || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(saved);
  window.toggleTheme = function(){ const now = body.classList.contains('dark') ? 'light' : 'dark'; setTheme(now); }

  // settings panel
  const settingsBtn = document.getElementById('settingsBtn');
  const panel = document.createElement('div');
  panel.className = 'settings-panel';
  panel.innerHTML = `<div style="font-weight:700;margin-bottom:8px">Settings</div>
    <div class="switch"><div>Theme</div><button id="themeToggle" class="cta small">Toggle</button></div>
    <div style="margin-top:10px" class="small">Page transitions enabled</div>`;
  document.body.appendChild(panel);
  settingsBtn.addEventListener('click', ()=> panel.classList.toggle('open'));
  document.getElementById('themeToggle').addEventListener('click', ()=> window.toggleTheme());
})();

// Page transition system (intercepts internal link clicks)
(function(){
  const overlay = document.createElement('div');
  overlay.className = 'page-overlay';
  overlay.innerHTML = '<div class="loader"></div>';
  document.body.appendChild(overlay);

  function showOverlay(){ overlay.classList.add('show'); }
  function hideOverlay(){ overlay.classList.remove('show'); }

  // Intercept clicks on same-origin internal links
  document.addEventListener('click', function(e){
    const a = e.target.closest('a');
    if(!a) return;
    const href = a.getAttribute('href');
    if(!href) return;
    if(href.startsWith('http') || href.startsWith('mailto:') || href.startsWith('#')) return;
    // allow ctrl/meta clicks
    if(e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    showOverlay();
    setTimeout(()=>{ window.location.href = href; }, 380);
  }, true);

  // Fade overlay on load
  window.addEventListener('load', ()=>{ setTimeout(()=>{ hideOverlay(); }, 200); });
})();

// News and Gallery loader (reads data files)
(function(){
  async function loadJSON(path){ try{ const r = await fetch(path); if(!r.ok) return null; return await r.json(); }catch(e){return null} }
  async function loadNews(){ const data = await loadJSON('data/news.json'); const container = document.getElementById('newsList'); if(!container) return; container.innerHTML=''; if(!data){ container.innerHTML='<div class="meta">Tidak ada berita.</div>'; return } data.slice(0,12).forEach(item=>{ const art=document.createElement('article'); art.className='card'; art.innerHTML=`<div class="meta">${item.date} • ${item.category}</div><h4>${item.title}</h4><p class="meta">${item.excerpt}</p><a href="${item.url||'#'}" class="meta">Baca Selanjutnya »</a>`; container.appendChild(art); }); }
  async function loadGallery(){ const data = await loadJSON('data/gallery.json'); const el = document.getElementById('galleryGrid'); if(!el) return; el.innerHTML=''; if(!data){ el.innerHTML='<div class="meta">Tidak ada gambar.</div>'; return } data.slice(0,24).forEach(img=>{ const a=document.createElement('a'); a.href=img.src; a.target='_blank'; a.className='card'; a.style.padding='0'; a.innerHTML=`<img src="${img.src}" alt="${img.caption||''}" style="width:100%;height:160px;object-fit:cover;border-radius:12px"/>`; el.appendChild(a); }); }
  document.addEventListener('DOMContentLoaded', ()=>{ loadNews(); loadGallery(); });
})();
