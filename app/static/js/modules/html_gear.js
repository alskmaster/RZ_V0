(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  function htmlToolbarHtml(){
    return `
      <div class="btn-group mb-2" role="group" aria-label="Editor toolbar">
        <button type="button" class="btn btn-outline-secondary btn-sm" data-cmd="bold"><i class="bi bi-type-bold"></i></button>
        <button type="button" class="btn btn-outline-secondary btn-sm" data-cmd="italic"><i class="bi bi-type-italic"></i></button>
        <button type="button" class="btn btn-outline-secondary btn-sm" data-cmd="underline"><i class="bi bi-type-underline"></i></button>
        <button type="button" class="btn btn-outline-secondary btn-sm" data-tag="h2">H2</button>
        <button type="button" class="btn btn-outline-secondary btn-sm" data-tag="h3">H3</button>
        <button type="button" class="btn btn-outline-secondary btn-sm" data-cmd="insertUnorderedList"><i class="bi bi-list-ul"></i></button>
        <button type="button" class="btn btn-outline-secondary btn-sm" data-cmd="insertOrderedList"><i class="bi bi-list-ol"></i></button>
        <button type="button" class="btn btn-outline-secondary btn-sm" data-link>Link</button>
        <button type="button" class="btn btn-outline-secondary btn-sm" data-hr>—</button>
        <div class="btn-group" role="group">
          <button type="button" class="btn btn-outline-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown">Inserir</button>
          <ul class="dropdown-menu">
            <li><a class="dropdown-item" href="#" data-table>Table 2x3</a></li>
            <li><a class="dropdown-item" href="#" data-image>Imagem (URL)</a></li>
            <li><a class="dropdown-item" href="#" data-callout="note">Bloco Nota</a></li>
            <li><a class="dropdown-item" href="#" data-callout="info">Bloco Informação</a></li>
            <li><a class="dropdown-item" href="#" data-callout="success">Bloco Sucesso</a></li>
            <li><a class="dropdown-item" href="#" data-callout="warning">Bloco Aviso</a></li>
            <li><a class="dropdown-item" href="#" data-callout="danger">Bloco Alerta</a></li>
          </ul>
        </div>
        <div class="btn-group ms-2" role="group">
          <button type="button" class="btn btn-outline-secondary btn-sm" data-align="left"><i class="bi bi-text-left"></i></button>
          <button type="button" class="btn btn-outline-secondary btn-sm" data-align="center"><i class="bi bi-text-center"></i></button>
          <button type="button" class="btn btn-outline-secondary btn-sm" data-align="right"><i class="bi bi-text-right"></i></button>
          <button type="button" class="btn btn-outline-secondary btn-sm" data-align="justify"><i class="bi bi-justify"></i></button>
        </div>
        <div class="btn-group ms-2" role="group">
          <button type="button" class="btn btn-outline-secondary btn-sm" data-size="small">A-</button>
          <button type="button" class="btn btn-outline-secondary btn-sm" data-size="big">A+</button>
        </div>
        <button type="button" class="btn btn-outline-dark btn-sm ms-2" id="toggleHtmlSrc">Fonte</button>
      </div>`;
  }

  function ensureHtmlModal(){
    let el = document.getElementById('customizeHtmlModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeHtmlModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Personalizar Módulo: Texto/HTML</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-12">
                <div class="d-flex align-items-center justify-content-between">
                  <div class="small text-muted">Placeholders rápidos: 
                    <span class="badge bg-light text-dark placeholder-chip" data-ph="{{client.name}}">{{client.name}}</span>
                    <span class="badge bg-light text-dark placeholder-chip" data-ph="{{client.sla}}">{{client.sla}}</span>
                    <span class="badge bg-light text-dark placeholder-chip" data-ph="{{period.ref}}">{{period.ref}}</span>
                    <span class="badge bg-light text-dark placeholder-chip" data-ph="{{date.today}}">{{date.today}}</span>
                  </div>
                  <div class="d-flex align-items-center gap-2">
                    <label class="form-label small mb-0" for="htmlTextAlign">Alinhamento</label>
                    <select id="htmlTextAlign" class="form-select form-select-sm" style="width: 140px;">
                      <option value="left">Esquerda</option>
                      <option value="center">Centralizado</option>
                      <option value="right">Direita</option>
                      <option value="justify">Justificado</option>
                    </select>
                    <label class="form-label small mb-0 ms-2" for="htmlBoxStyle">Estilo do bloco</label>
                    <select id="htmlBoxStyle" class="form-select form-select-sm" style="width: 160px;">
                      <option value="none">Nenhum</option>
                      <option value="note">Nota</option>
                      <option value="info">Informação</option>
                      <option value="success">Sucesso</option>
                      <option value="warning">Aviso</option>
                      <option value="danger">Alerta</option>
                    </select>
                  </div>
                </div>
                ${htmlToolbarHtml()}
                <div id="htmlEditor" class="form-control" style="min-height: 220px;" contenteditable="true"></div>
                <textarea id="htmlSource" class="form-control mt-2 d-none" style="min-height: 220px; font-family: monospace;"></textarea>
                <div class="small text-muted mt-2">Dica: cole conteúdo do Word/Docs ou edite aqui. Tags básicas são suportadas (negrito, itálico, listas, títulos).</n>
              </div>
            </div>
            <hr/>
            <div class="row g-3">
              <div class="col-12 col-md-6">
                <label class="form-label">Modelos rápidos</label>
                <div class="d-grid gap-2">
                  <button type="button" class="btn btn-outline-secondary btn-sm quick-tpl" data-tpl="exec">Resumo Executivo</button>
                  <button type="button" class="btn btn-outline-secondary btn-sm quick-tpl" data-tpl="notes">Notas Técnicas</button>
                  <button type="button" class="btn btn-outline-secondary btn-sm quick-tpl" data-tpl="next">Próximos Passos</button>
                  <button type="button" class="btn btn-outline-secondary btn-sm quick-tpl" data-tpl="destaques">Destaques</button>
                  <button type="button" class="btn btn-outline-secondary btn-sm quick-tpl" data-tpl="metodologia">Metodologia</button>
                </div>
              </div>
              <div class="col-12 col-md-6">
                <div class="alert alert-info small mb-0">
                  Campos dinâmicos:
                  <ul class="mb-0">
                    <li>{{client.name}} — Nome do cliente</li>
                    <li>{{client.sla}} — Meta de SLA do cliente</li>
                    <li>{{period.ref}} — Mês de referência</li>
                    <li>{{date.today}} — Data atual</li>
                    <li>{{period.start}} / {{period.end}}</li>
                    <li>{{period.ref_short}} — mm/aaaa</li>
                    <li>{{system.company}} — Sua empresa</li>
                    <li>{{hosts.count}} — Total de hosts</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
            <button type="button" class="btn btn-primary" id="saveHtmlBtn">Salvar</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);

    // Toolbar handlers
    const editor = document.getElementById('htmlEditor');
    const source = document.getElementById('htmlSource');
    tpl.querySelectorAll('[data-cmd]').forEach(btn => {
      btn.addEventListener('click', () => document.execCommand(btn.getAttribute('data-cmd'), false, null));
    });
    tpl.querySelectorAll('[data-tag]').forEach(btn => {
      btn.addEventListener('click', () => {
        const tag = btn.getAttribute('data-tag');
        document.execCommand('formatBlock', false, tag);
      });
    });
    const linkBtn = tpl.querySelector('[data-link]');
    linkBtn.addEventListener('click', () => {
      const url = prompt('URL do link:');
      if (url) document.execCommand('createLink', false, url);
    });
    const hrBtn = tpl.querySelector('[data-hr]');
    hrBtn.addEventListener('click', () => document.execCommand('insertHorizontalRule'));
    // Inserções
    tpl.querySelector('[data-table]').addEventListener('click', (e)=>{
      e.preventDefault();
      const html = '<table style="width:100%; border-collapse: collapse;" border="1"><tbody>'+
                   '<tr><td>&nbsp;</td><td>&nbsp;</td></tr>'+
                   '<tr><td>&nbsp;</td><td>&nbsp;</td></tr>'+
                   '<tr><td>&nbsp;</td><td>&nbsp;</td></tr>'+
                   '</tbody></table>';
      insertHtmlAtCursor(editor, html);
    });
    tpl.querySelector('[data-image]').addEventListener('click', (e)=>{
      e.preventDefault();
      const url = prompt('URL da imagem:');
      if (url) insertHtmlAtCursor(editor, `<img src="${url}" style="max-width:100%;"/>`);
    });
    tpl.querySelectorAll('[data-callout]').forEach(a => {
      a.addEventListener('click', (e)=>{
        e.preventDefault();
        const kind = a.getAttribute('data-callout');
        insertHtmlAtCursor(editor, `<div class="callout callout-${kind}"><p><strong>${kind.toUpperCase()}:</strong> seu texto aqui...</p></div>`);
      });
    });
    // Alinhamento local
    tpl.querySelectorAll('[data-align]').forEach(btn => {
      btn.addEventListener('click', ()=>{
        const m = btn.getAttribute('data-align');
        const cmd = {left:'justifyLeft',center:'justifyCenter',right:'justifyRight',justify:'justifyFull'}[m];
        if (cmd) document.execCommand(cmd, false, null);
      });
    });
    // Tamanho do texto
    tpl.querySelectorAll('[data-size]').forEach(btn => {
      btn.addEventListener('click', ()=>{
        const kind = btn.getAttribute('data-size');
        wrapSelectionWithSpan(editor, kind === 'small' ? 'text-small' : 'text-big');
      });
    });
    // Toggle fonte
    tpl.querySelector('#toggleHtmlSrc').addEventListener('click', ()=>{
      const showing = !source.classList.contains('d-none');
      if (showing) {
        editor.innerHTML = source.value;
        source.classList.add('d-none');
        editor.classList.remove('d-none');
      } else {
        source.value = editor.innerHTML;
        editor.classList.add('d-none');
        source.classList.remove('d-none');
      }
    });
    // Placeholders insertion
    tpl.querySelectorAll('.placeholder-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const ph = chip.getAttribute('data-ph');
        document.execCommand('insertText', false, ph);
        editor.focus();
      });
    });
    // Quick templates
    tpl.querySelectorAll('.quick-tpl').forEach(btn => {
      btn.addEventListener('click', () => {
        const kind = btn.getAttribute('data-tpl');
        const content = quickTemplate(kind);
        editor.innerHTML = content;
      });
    });
    return document.getElementById('customizeHtmlModal');
  }

  function quickTemplate(kind){
    switch(kind){
      case 'exec':
        return `<h2>Resumo Executivo — {{period.ref}}</h2>
<p>Cliente: <strong>{{client.name}}</strong></p>
<p>Este relatório apresenta os indicadores principais do ambiente no período informado. SLA contratado: <strong>{{client.sla}}%</strong>.</p>
<ul>
  <li>Disponibilidade e estabilidade geral do ambiente</li>
  <li>Principais indisponibilidades e causas</li>
  <li>Recomendações de melhoria</li>
 </ul>`;
      case 'notes':
        return `<h3>Notas Técnicas</h3>
<ul>
  <li>Principais eventos de manutenção e mudanças</li>
  <li>Observações sobre coleta/métricas</li>
  <li>Riscos e ações mitigatórias</li>
 </ul>`;
      case 'destaques':
        return `<div class="callout callout-info"><h3>Destaques — {{period.ref_short}}</h3>
<ul>
  <li>Pontos positivos do período</li>
  <li>Oportunidades de melhoria</li>
  <li>Itens críticos acompanhados</li>
</ul></div>`;
      case 'metodologia':
        return `<h3>Metodologia</h3>
<p>Coletas realizadas entre {{period.start}} e {{period.end}} utilizando a plataforma Zabbix. Indicadores consolidados por host e agregados mensalmente.</p>`;
      case 'next':
      default:
        return `<h3>Próximos Passos</h3>
<ol>
  <li>Alinhar plano de ação com o time do cliente</li>
  <li>Priorizar melhorias com maior impacto em SLA</li>
  <li>Acompanhar resultados no próximo ciclo</li>
 </ol>`;
    }
  }

  window.ModuleCustomizers['html'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureHtmlModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        editor: document.getElementById('htmlEditor'),
        source: document.getElementById('htmlSource'),
        align: document.getElementById('htmlTextAlign'),
        box: document.getElementById('htmlBoxStyle'),
        saveBtn: document.getElementById('saveHtmlBtn')
      };
    },
    load(options){
      this._ensure();
      const o = options || {};
      this.elements.editor.innerHTML = o.content || '';
      this.elements.align.value = o.text_align || 'left';
      this.elements.box.value = o.box_style || 'none';
      // Quando alternar para fonte, sincronizar
      this.elements.source.value = this.elements.editor.innerHTML;
      this.elements.saveBtn.onclick = null;
      this.elements.saveBtn.addEventListener('click', () => {
        if (this._onSave) this._onSave(this.save());
        this.modal.hide();
      }, { once: true });
    },
    save(){
      return {
        content: this.elements.editor.innerHTML || '',
        text_align: this.elements.align.value || 'left',
        box_style: this.elements.box.value || 'none'
      };
    }
  };

  // Helpers
  function insertHtmlAtCursor(editor, html){
    editor.focus();
    document.execCommand('insertHTML', false, html);
  }
  function wrapSelectionWithSpan(editor, className){
    editor.focus();
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    const span = document.createElement('span');
    span.className = className;
    range.surroundContents(span);
  }
})();
