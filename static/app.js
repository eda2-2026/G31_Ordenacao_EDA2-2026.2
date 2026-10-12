// Funções compartilhadas pelas páginas. Toda a ordenação acontece no Python;
// aqui só se busca o resultado na API e se desenha na tela.

const SPRITES = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon';

// recebe o aluno: usa pokemon_id e, se ele tiver, a versão shiny
function artwork(a) {
  return `${SPRITES}/other/official-artwork/${a.shiny ? 'shiny/' : ''}${a.pokemon_id}.png`;
}

function esc(texto) {
  return String(texto ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function num(n) {
  return Number(n).toLocaleString('pt-BR');
}

function ira(valor) {
  return Number(valor).toFixed(4).replace('.', ',');
}

function dataHora(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }) + ' ' +
    d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function corIra(valor) {
  if (valor >= 4) return 'bg-emerald-500';
  if (valor >= 3) return 'bg-sigaa-500';
  if (valor >= 2) return 'bg-amber-500';
  return 'bg-poke-500';
}

async function api(url, opcoes = {}) {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...opcoes,
    body: opcoes.body ? JSON.stringify(opcoes.body) : undefined,
  });
  const dados = await resp.json().catch(() => ({}));
  if (!resp.ok) throw Object.assign(new Error(dados.erro || `Erro ${resp.status}`), { dados });
  return dados;
}

let toastTimer;
function toast(msg, tipo = 'ok') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = el.className.replace(/bg-\S+/g, '') + (tipo === 'erro' ? ' bg-poke-600' : ' bg-slate-900');
  el.style.opacity = 1;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.style.opacity = 0), 3200);
}

async function comCarregando(botao, tarefa) {
  const original = botao.innerHTML;
  botao.disabled = true;
  botao.innerHTML = '<span class="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"></span> Processando…';
  try {
    return await tarefa();
  } finally {
    botao.disabled = false;
    botao.innerHTML = original;
  }
}

// nome do Pokémon em português não existe na PokéAPI; usa o nome em inglês
const cacheNomes = {};
async function nomePokemon(id) {
  if (cacheNomes[id]) return cacheNomes[id];
  try {
    const r = await fetch(`https://pokeapi.co/api/v2/pokemon-species/${id}`);
    const d = await r.json();
    cacheNomes[id] = d.names.find(n => n.language.name === 'en')?.name || d.name;
  } catch {
    cacheNomes[id] = `#${id}`;
  }
  return cacheNomes[id];
}

function avatar(a, tamanho = 'h-10 w-10') {
  return `<span class="inline-flex ${tamanho} shrink-0 items-center justify-center rounded-full bg-gradient-to-b from-slate-100 to-slate-200 ${a.shiny ? 'ring-2 ring-amber-400' : 'ring-1 ring-slate-200'}" title="${a.shiny ? 'Shiny ✨' : ''}">
    <img src="${artwork(a)}" alt="" loading="lazy" class="h-[85%] w-[85%] object-contain"></span>`;
}
