(() => {
  const select = document.getElementById('site-lang');
  const key = 'marsnav.lang';
  const native = select.dataset.native;
  const languages = {en:'English', es:'Español', de:'Deutsch', fr:'Français', ja:'日本語', it:'Italiano', ko:'한국어', 'es-419':'Español latino', pt:'Português'};
  const originals = new WeakMap();
  const cache = new Map();
  let selected = native;
  let scheduled;
  let running = false;
  let pending = false;
  try { selected = localStorage.getItem(key) || native; } catch {}
  if (!Object.hasOwn(languages, selected)) selected = native;

  for (const [code, name] of Object.entries(languages)) select.add(new Option(name, code));
  window.marsnavLang = () => selected === 'es' ? 'es' : 'en';

  const excluded = 'script,style,noscript,code,pre,#site-lang,[contenteditable],textarea,input,[data-no-translate],.leaflet-control-attribution,.modebar';
  const eligible = value => /\p{L}/u.test(value) && !/^(?:https?:|www\.)/i.test(value.trim());

  async function translate(entries, language) {
    const separator = '\nZXQZXQ\n';
    const query = new URLSearchParams({client:'gtx', sl:'auto', tl:language, dt:'t', q:entries.join(separator)});
    const response = await fetch('https://translate.googleapis.com/translate_a/single?' + query);
    if (!response.ok) throw new Error('Translation unavailable');
    const [sentences] = await response.json();
    const result = sentences.map(sentence => sentence[0]).join('').split(/\s*ZXQZXQ\s*/i);
    if (result.length !== entries.length) throw new Error('Translation segment count changed');
    return result;
  }

  function queue() {
    clearTimeout(scheduled);
    scheduled = setTimeout(async () => {
      if (running) { pending = true; return; }
      running = true;
      try { await render(); }
      finally {
        running = false;
        if (pending) { pending = false; queue(); }
      }
    }, 140);
  }

  async function render() {
    const language = selected;
    if (language === 'en' || language === 'es') return;
    const nodes = new Map();
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node; (node = walker.nextNode());) {
      const el = node.parentElement;
      if (!el || el.closest(excluded) || !el.getClientRects().length) continue;
      const value = node.nodeValue.trim();
      if (!eligible(value)) continue;
      const previous = originals.get(node);
      if (previous?.translated === node.nodeValue) continue;
      if (!nodes.has(value)) nodes.set(value, []);
      nodes.get(value).push(node);
    }
    function apply(input, output) {
      if (selected !== language || !output) return;
      for (const node of nodes.get(input)) {
        if (!node.isConnected || node.nodeValue.trim() !== input || node.nodeValue === output) continue;
        const source = node.nodeValue;
        const translated = source.match(/^\s*/)[0] + output.trim() + source.match(/\s*$/)[0];
        originals.set(node, {source, translated});
        node.nodeValue = translated;
      }
    }
    const batches = [];
    let batch = [], size = 0;
    for (const input of nodes.keys()) {
      const stored = cache.get(language + '\0' + input);
      if (stored) { apply(input, stored); continue; }
      if (size + input.length > 3400 && batch.length) { batches.push(batch); batch = []; size = 0; }
      batch.push(input);
      size += input.length + 8;
    }
    if (batch.length) batches.push(batch);
    // Keep the number of concurrent requests small on long guide pages.
    for (let index = 0; index < batches.length && selected === language; index += 4) {
      await Promise.allSettled(batches.slice(index, index + 4).map(async inputs => {
        const outputs = await translate(inputs, language);
        inputs.forEach((input, i) => {
          cache.set(language + '\0' + input, outputs[i]);
          apply(input, outputs[i]);
        });
      }));
    }
  }

  function setLanguage() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node; (node = walker.nextNode());) {
      const previous = originals.get(node);
      if (previous?.translated === node.nodeValue) node.nodeValue = previous.source;
      originals.delete(node);
    }
    select.value = selected;
    document.querySelectorAll('nav[aria-label=Sections] a').forEach(link => {
      link.textContent = window.marsnavLang() === 'es' ? link.dataset.labelEs : link.dataset.labelEn;
    });
    dispatchEvent(new Event('marsnav-lang'));
    document.documentElement.lang = selected;
    queue();
  }

  select.addEventListener('change', () => {
    selected = select.value;
    try { localStorage.setItem(key, selected); } catch {}
    setLanguage();
  });
  addEventListener('DOMContentLoaded', () => {
    setLanguage();
    new MutationObserver(records => {
      if (records.some(record => originals.get(record.target)?.translated !== record.target.nodeValue || record.type === 'childList')) queue();
    }).observe(document.body, {subtree:true, childList:true, characterData:true});
    document.addEventListener('toggle', queue, true);
  });
  // Available synchronously to each page's inline scripts during parsing.
  select.value = selected;
})();
