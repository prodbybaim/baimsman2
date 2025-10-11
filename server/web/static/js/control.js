let token = window.initialToken || '';
if (token) document.getElementById('tokenInput').value = token;

const api = (path, opts={})=>{
  opts.headers = opts.headers||{};
  if(token) opts.headers['Authorization'] = 'Bearer '+token;
  return fetch(path, opts).then(r=>r.json().then(b=>({ok:r.ok, status:r.status, body:b})))
}

async function listArticles(){
  const res = await api('/api/articles');
  if(!res.ok){ alert('unauthorized or error'); return }
  const tbody = document.querySelector('#articlesTable tbody');
  tbody.innerHTML='';
  for(const a of res.body){
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${a.id}</td><td>${a.title}</td><td>${a.created}</td><td>
      <button data-id="${a.id}" class="edit">Edit</button>
      <button data-id="${a.id}" class="del">Del</button></td>`;
    tbody.appendChild(tr);
  }
}

document.addEventListener('click', async e=>{
  if(e.target.id=='btnRefresh') return listArticles();
  if(e.target.id=='btnGetToken'){
    const pass = prompt('admin password');
    if(!pass) return;
    const r = await fetch('/api/token',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pass})});
    const j = await r.json();
    if(!r.ok){ alert('bad password'); return }
    token = j.token; document.getElementById('tokenInput').value = token;
    listArticles();
  }
  if(e.target.classList.contains('edit')){
    const id = e.target.dataset.id;
    const rr = await api('/api/article/'+id);
    if(!rr.ok){ alert('error'); return }
    document.getElementById('editor').style.display='block';
    document.getElementById('editTitle').value = rr.body.title;
    document.getElementById('editContent').value = rr.body.content;
    document.getElementById('saveBtn').onclick = async ()=>{
      const title = document.getElementById('editTitle').value;
      const content = document.getElementById('editContent').value;
      const upd = await fetch('/api/article/'+id,{method:'PUT',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify({title,content})});
      if(upd.ok){ alert('saved'); document.getElementById('editor').style.display='none'; listArticles() }
      else { alert('save failed') }
    }
  }
  if(e.target.classList.contains('del')){
    if(!confirm('delete?')) return;
    const id = e.target.dataset.id;
    const d = await fetch('/api/article/'+id,{method:'DELETE',headers:{'Authorization':'Bearer '+token}});
    if(d.ok) listArticles(); else alert('delete failed');
  }
  if(e.target.id=='btnNew'){
    document.getElementById('editor').style.display='block';
    document.getElementById('editTitle').value='';
    document.getElementById('editContent').value='';
    document.getElementById('saveBtn').onclick = async ()=>{
      const title = document.getElementById('editTitle').value;
      const content = document.getElementById('editContent').value;
      const c = await fetch('/api/article',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify({title,content})});
      if(c.ok){ alert('created'); document.getElementById('editor').style.display='none'; listArticles(); }
      else { alert('create failed'); }
    }
  }
});

document.getElementById('btnRefresh').addEventListener('click', listArticles);
document.getElementById('tokenInput').addEventListener('change', e=>{ token = e.target.value });
listArticles();
