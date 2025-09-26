document.addEventListener('DOMContentLoaded', function () {
    // --- ELEMENTOS DO DOM ---
    const clientSelect = document.getElementById('client_id');
    const dateFromInput = document.getElementById('date_from');
    const dateToInput = document.getElementById('date_to');
    const moduleTypeSelect = document.getElementById('module-type-select');
    const moduleTitleInput = document.getElementById('module-title-input');
    const newPageCheck = document.getElementById('module-newpage-check');
    const addModuleBtn = document.getElementById('add-module-btn');
    const layoutList = document.getElementById('report-layout-list');
    const jsonTextarea = document.getElementById('report_layout_json');
    const reportForm = document.getElementById('report-form');
    const generateBtn = document.getElementById('generate-btn');
    const statusArea = document.getElementById('status-area');
    const statusMessage = document.getElementById('status-message');
    const downloadLink = document.getElementById('download-link');
    const templateSelector = document.getElementById('templateSelector');
    const loadTemplateBtn = document.getElementById('loadTemplateBtn');
    const saveTemplateBtn = document.getElementById('saveTemplateBtn');
    const templateNameInput = document.getElementById('templateNameInput');
    const updateTemplateBtn = document.getElementById('updateTemplateBtn');
    const deleteTemplateBtn = document.getElementById('deleteTemplateBtn');
    const confirmSaveTemplateBtn = document.getElementById('confirmSaveTemplateBtn');
    const saveTemplateModalEl = document.getElementById('saveTemplateModal');
    const saveTemplateModal = saveTemplateModalEl ? new bootstrap.Modal(saveTemplateModalEl) : null;
    const saveTemplateModalLabel = document.getElementById('saveTemplateModalLabel');
    const csrfToken = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

    // --- ESTADO DA APLICAÇÃO ---
    let reportLayout = [];
    let availableModules = [];
    let currentModuleToCustomize = null;
    let activePoll = null; // controle para polling de status
    let savedTemplates = [];
    let activeTemplateId = null;
    let templateAction = 'create';
    let templateBeingEditedId = null;

    // ===================================================================================
    // --- CENTRO DE COMANDO DE CUSTOMIZAÇÃO DE MÓDULOS ---
    // ===================================================================================
    const moduleCustomizers = {
        'sla': {
            modal: new bootstrap.Modal(document.getElementById('customizeSlaModal')),
            elements: {
                hideSummary: document.getElementById('slaHideSummaryCheck'),
                comparePrevMonth: document.getElementById('slaComparePrevMonthCheck'),
                showIp: document.getElementById('slaShowIpCheck'),
                showDowntime: document.getElementById('slaShowDowntimeCheck'),
                showPrevSla: document.getElementById('slaShowPreviousSlaCheck'),
                showImprovement: document.getElementById('slaShowImprovementCheck'),
                showGoal: document.getElementById('slaShowGoalCheck'),
                saveBtn: document.getElementById('saveSlaCustomizationBtn')
            },
            load: function(options) {
                this.elements.hideSummary.checked = options.hide_summary || false;
                this.elements.comparePrevMonth.checked = options.compare_to_previous_month || false;
                this.elements.showIp.checked = options.show_ip || false;
                this.elements.showDowntime.checked = options.show_downtime || false;
                this.elements.showGoal.checked = options.show_goal || false;

                const isCompareChecked = this.elements.comparePrevMonth.checked;
                this.elements.showPrevSla.disabled = !isCompareChecked;
                this.elements.showImprovement.disabled = !isCompareChecked;
                this.elements.showPrevSla.checked = isCompareChecked && (options.show_previous_sla || false);
                this.elements.showImprovement.checked = isCompareChecked && (options.show_improvement || false);
            },
            save: function() {
                return {
                    hide_summary: this.elements.hideSummary.checked,
                    compare_to_previous_month: this.elements.comparePrevMonth.checked,
                    show_ip: this.elements.showIp.checked,
                    show_downtime: this.elements.showDowntime.checked,
                    show_previous_sla: this.elements.showPrevSla.checked,
                    show_improvement: this.elements.showImprovement.checked,
                    show_goal: this.elements.showGoal.checked
                };
            }
        },
        'top_hosts': {
            modal: new bootstrap.Modal(document.getElementById('customizeTopHostsModal')),
            elements: {
                topN: document.getElementById('topHostsCount'),
                showSummary: document.getElementById('topHostsShowSummaryChartCheck'),
                showDiagnosis: document.getElementById('topHostsShowDetailedDiagnosisCheck'),
                chartType: document.getElementById('topHostsBreakdownChartType'),
                saveBtn: document.getElementById('saveTopHostsCustomizationBtn')
            },
            load: function(options) {
                this.elements.topN.value = options.top_n || 5;
                this.elements.showSummary.checked = options.show_summary_chart !== false;
                this.elements.showDiagnosis.checked = options.show_detailed_diagnosis !== false;
                this.elements.chartType.value = options.chart_type || 'table';
            },
            save: function() {
                return {
                    top_n: parseInt(this.elements.topN.value, 10),
                    show_summary_chart: this.elements.showSummary.checked,
                    show_detailed_diagnosis: this.elements.showDiagnosis.checked,
                    chart_type: this.elements.chartType.value
                };
            }
        }
    };

    // Registro pluginável: permite que arquivos JS externos adicionem customizações
    if (window.ModuleCustomizers && typeof window.ModuleCustomizers === 'object') {
        Object.assign(moduleCustomizers, window.ModuleCustomizers);
    }
    // Remove customização inline do legado, usaremos o SLA Plus em plugin separado
    if (moduleCustomizers['sla']) {
        delete moduleCustomizers['sla'];
    }
    // ===================================================================================

    // --- FUNÇÕES AUXILIARES ---

    function logDebug(event, details = {}) {
        console.debug(`[gerar_form] ${event}`, details);
        window.__gerarFormDebug = window.__gerarFormDebug || [];
        window.__gerarFormDebug.push({ ts: new Date().toISOString(), event, details });
    }

    function safeUUID() {
        if (window.crypto && crypto.randomUUID) {
            return crypto.randomUUID();
        }
        return 'id-' + Math.random().toString(36).substring(2, 11);
    }

    function renderLayoutList() {
        layoutList.innerHTML = '';
        if (reportLayout.length === 0) {
            layoutList.innerHTML = '<li class="list-group-item text-muted">Nenhum módulo adicionado.</li>';
            return;
        }
        reportLayout.forEach(module => {
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center';
            li.dataset.moduleId = module.id;

            const moduleName = availableModules.find(m => m.type === module.type)?.name || module.type;
            const titleDisplay = module.title ? `"${module.title}"` : '';
            // Detecta se há customizer registrado para o módulo.
            // Fall-back: garante o botão para tipos conhecidos mesmo se o registro atrasar.
            const knownCustomizable = new Set(['incidents_table', 'incidents_chart', 'wifi', 'disk', 'disk_table', 'disk_chart', 'traffic_in_table', 'traffic_in_chart', 'traffic_out_table', 'traffic_out_chart', 'latency_table', 'latency_chart', 'loss_table', 'loss_chart', 'cpu_table', 'cpu_chart', 'mem_table', 'mem_chart', 'agent_status', 'mttr', 'critical_performance', 'capacity_forecast', 'incident_availability', 'resilience_panel', 'resilience_services', 'recurring_problems', 'root_cause_top_triggers', 'unavailability_heatmap', 'html', 'inventory']);
            const isCustomizable = (
                (module.type in moduleCustomizers) ||
                (window.ModuleCustomizers && (module.type in window.ModuleCustomizers)) ||
                knownCustomizable.has(module.type)
            );

            li.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="bi bi-grip-vertical me-3" style="cursor: grab;"></i>
                    <div>
                        <span class="fw-bold">${moduleName}</span>
                        <small class="d-block text-muted">${titleDisplay}</small>
                    </div>
                </div>
                <div class="btn-group">
                    ${isCustomizable ? `<button type="button" class="btn btn-sm btn-outline-secondary customize-module-btn me-2" data-module-id="${module.id}" title="Personalizar"><i class="bi bi-gear"></i></button>` : ''}
                    <button type="button" class="btn btn-sm btn-outline-danger remove-module-btn" data-module-id="${module.id}" title="Remover">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            layoutList.appendChild(li);
        });
        jsonTextarea.value = JSON.stringify(reportLayout);
    }

    async function fetchClientData(clientId) {
        if (!clientId) {
            moduleTypeSelect.innerHTML = '<option>Selecione um cliente primeiro</option>';
            moduleTypeSelect.disabled = true;
            addModuleBtn.disabled = true;
            return;
        }
        moduleTypeSelect.innerHTML = '<option>Carregando módulos ...</option>';
        moduleTypeSelect.disabled = true;
        addModuleBtn.disabled = true;

        const url = URLS.get_modules.replace('0', String(clientId));
        logDebug('fetchClientData.start', { url });

        try {
            const response = await fetch(url, { headers: { 'Accept': 'application/json' }});
            if (!response.ok) {
                const rawText = await response.text().catch(() => '');
                logDebug('fetchClientData.error', { status: response.status, rawText });
                moduleTypeSelect.innerHTML = '<option>Erro ao carregar módulos</option>';
                return;
            }

            const data = await response.json().catch(err => {
                logDebug('fetchClientData.jsonError', { err: String(err) });
                return null;
            });

            if (!data || data.error) {
                logDebug('fetchClientData.backendError', { error: data?.error });
                moduleTypeSelect.innerHTML = '<option>Erro ao carregar módulos</option>';
                return;
            }

            availableModules = Array.isArray(data.available_modules) ? data.available_modules : [];
            // Remover legados duplicados (latency/loss/cpu) do builder
            availableModules = availableModules.filter(m => !['latency','loss','cpu'].includes(m.type));
            logDebug('fetchClientData.success', { count: availableModules.length });

            // Agrupamento por categorias (optgroups) para melhor usabilidade
            moduleTypeSelect.innerHTML = '';
            const TYPE_TO_CATEGORY = {
                // Disponibilidade / SLA
                'incident_availability': 'Disponibilidade / SLA',
                'uptime_summary': 'Disponibilidade / SLA',
                'kpi': 'Disponibilidade / SLA', 'sla_table': 'Disponibilidade / SLA',
                'sla_chart': 'Disponibilidade / SLA', 'sla_plus': 'Disponibilidade / SLA',
                'sla_incidents_table': 'Disponibilidade / SLA',
                'resilience_panel': 'Disponibilidade / SLA', 'resilience_services': 'Disponibilidade / SLA',
                'top_hosts': 'Disponibilidade / SLA', 'top_problems': 'Disponibilidade / SLA',
                'stress': 'Disponibilidade / SLA',
                // Incidentes
                'incidents_table': 'Incidentes', 'incidents_chart': 'Incidentes', 'unavailability_heatmap': 'Incidentes',
                'root_cause_top_triggers': 'Incidentes', 'mttr': 'Incidentes', 'recurring_problems': 'Incidentes',
                'softdesk_root_cause': 'Incidentes',
                // Desempenho
                'cpu_table': 'Desempenho', 'cpu_chart': 'Desempenho',
                'mem_table': 'Desempenho', 'mem_chart': 'Desempenho',
                'disk': 'Desempenho', 'disk_table': 'Desempenho', 'disk_chart': 'Desempenho',
                'critical_performance': 'Desempenho',
                // Rede (Ping)
                'latency_table': 'Rede (Ping)', 'latency_chart': 'Rede (Ping)',
                'loss_table': 'Rede (Ping)', 'loss_chart': 'Rede (Ping)',
                // Rede (Trafego)
                'traffic_in': 'Rede (Trafego)', 'traffic_in_table': 'Rede (Trafego)', 'traffic_in_chart': 'Rede (Trafego)',
                'traffic_out': 'Rede (Trafego)', 'traffic_out_table': 'Rede (Trafego)', 'traffic_out_chart': 'Rede (Trafego)',
                // Wi-Fi
                'wifi': 'Wi-Fi',
                // Operacao
                'agent_status': 'Operacao',
                // Planejamento
                'capacity_forecast': 'Planejamento',
                // Executivo
                'executive_summary': 'Executivo',
                // Inventario & Conteudo
                'inventory': 'Inventario & Conteudo', 'html': 'Inventario & Conteudo'
            };
            const CATEGORY_ORDER = [
                'Disponibilidade / SLA',
                'Incidentes',
                'Desempenho',
                'Rede (Ping)',
                'Rede (Trafego)',
                'Wi-Fi',
                'Operacao',
                'Planejamento',
                'Executivo',
                'Inventario & Conteudo'
            ];
            const buckets = {};
            availableModules.forEach(m => {
                const cat = TYPE_TO_CATEGORY[m.type] || 'Outros';
                if (!buckets[cat]) buckets[cat] = [];
                buckets[cat].push(m);
            });
            const orderedCats = CATEGORY_ORDER.concat(Object.keys(buckets).filter(c => !CATEGORY_ORDER.includes(c)).sort());
            let totalOptions = 0;
            orderedCats.forEach(cat => {
                if (!buckets[cat] || buckets[cat].length === 0) return;
                const og = document.createElement('optgroup');
                og.label = cat;
                // Ordena alfabeticamente por nome amigável
                buckets[cat].sort((a, b) => String(a.name).localeCompare(String(b.name), 'pt-BR'));
                buckets[cat].forEach(m => {
                    og.appendChild(new Option(m.name, m.type));
                    totalOptions += 1;
                });
                moduleTypeSelect.appendChild(og);
            });
            if (totalOptions > 0) {
                moduleTypeSelect.disabled = false;
                addModuleBtn.disabled = false;
            } else {
                moduleTypeSelect.innerHTML = '<option>Nenhum módulo disponível</option>';
            }
        } catch (error) {
            logDebug('fetchClientData.exception', { error: String(error) });
            moduleTypeSelect.innerHTML = '<option>Erro ao carregar módulos</option>';
        }
    }

    function resetStatusArea() {
        statusArea.style.display = 'none';
        statusMessage.textContent = 'Iniciando...';
        statusArea.className = 'alert alert-info mt-4';
        downloadLink.classList.add('disabled');
        downloadLink.href = '#';
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="bi bi-file-earmark-pdf"></i> Gerar Relatório';
    }

    function withCsrf(headers = {}) {
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        return headers;
    }

    function findTemplateById(templateId) {
        if (templateId === null || templateId === undefined) return null;
        const idNum = Number(templateId);
        if (Number.isNaN(idNum)) return null;
        return savedTemplates.find(t => Number(t.id) === idNum) || null;
    }

    function renderSavedTemplates(selectedId = null) {
        if (!templateSelector) return;
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = 'Carregar Template...';
        templateSelector.innerHTML = '';
        templateSelector.appendChild(placeholder);
        savedTemplates.forEach(t => {
            const option = new Option(t.name || `Template #${t.id}`, t.layout_json || '');
            option.dataset.templateId = t.id;
            if (selectedId && Number(selectedId) === Number(t.id)) {
                option.selected = true;
            }
            templateSelector.appendChild(option);
        });
    }

    async function refreshSavedTemplates(selectedId = null) {
        if (!URLS || !URLS.get_templates) return;
        try {
            const response = await fetch(URLS.get_templates, { headers: { 'Accept': 'application/json' } });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            savedTemplates = Array.isArray(data) ? data : [];
            renderSavedTemplates(selectedId);
        } catch (error) {
            logDebug('templates.refresh.error', { error: String(error) });
        }
    }

    function getSelectedTemplateInfo() {
        if (!templateSelector) return null;
        const option = templateSelector.options[templateSelector.selectedIndex];
        if (!option || !option.dataset.templateId) return null;
        const templateId = Number(option.dataset.templateId);
        const record = findTemplateById(templateId);
        return record ? { id: templateId, option, record } : null;
    }

    function prepareTemplateModal(action, templateRecord) {
        templateAction = action;
        templateBeingEditedId = templateRecord ? templateRecord.id : null;
        if (saveTemplateModalLabel) {
            saveTemplateModalLabel.textContent = action === 'update' ? 'Atualizar Template' : 'Salvar Layout como Template';
        }
        if (templateNameInput) {
            templateNameInput.value = templateRecord ? (templateRecord.name || '') : '';
            templateNameInput.focus();
        }
    }

    function bootstrapSavedTemplatesFromDom() {
        if (!templateSelector) return;
        const options = Array.from(templateSelector.options || []);
        savedTemplates = options
            .map(option => {
                const idAttr = option.dataset ? option.dataset.templateId : null;
                if (!idAttr) return null;
                const idNum = Number(idAttr);
                if (Number.isNaN(idNum)) return null;
                return {
                    id: idNum,
                    name: option.textContent || `Template #${idAttr}`,
                    layout_json: option.value || '[]'
                };
            })
            .filter(Boolean);
    }

    // --- EVENTOS ---

    clientSelect.addEventListener('change', () => {
        fetchClientData(clientSelect.value);
        reportLayout = [];
        renderLayoutList();
        activeTemplateId = null;
        if (templateSelector) {
            templateSelector.selectedIndex = 0;
        }
    });

    addModuleBtn.addEventListener('click', () => {
        const moduleType = moduleTypeSelect.value;
        if (!moduleType) return;
        reportLayout.push({
            id: safeUUID(),
            type: moduleType,
            title: moduleTitleInput.value.trim(),
            newPage: newPageCheck.checked,
            custom_options: {}
        });
        renderLayoutList();
        moduleTitleInput.value = '';
        newPageCheck.checked = false;
    });

    layoutList.addEventListener('click', (e) => {
        const targetBtn = e.target.closest('button');
        if (!targetBtn) return;

        const moduleId = targetBtn.dataset.moduleId;
        const module = reportLayout.find(m => m.id === moduleId);
        if (!module) return;

        if (targetBtn.classList.contains('remove-module-btn')) {
            reportLayout = reportLayout.filter(m => m.id !== moduleId);
            renderLayoutList();
        } else if (targetBtn.classList.contains('customize-module-btn')) {
            currentModuleToCustomize = module;
            try { window.currentModuleToCustomize = module; } catch(e) {}
            const customizer = moduleCustomizers[module.type] || (window.ModuleCustomizers && window.ModuleCustomizers[module.type]);
            if (customizer) {
                // Garante que o modal exista, mesmo para plugins carregados depois
                if (!customizer.modal && typeof customizer._ensure === 'function') {
                    customizer._ensure();
                }
                if (typeof customizer.load === 'function') {
                    customizer.load(module.custom_options || {});
                }
                if (customizer.modal && typeof customizer.modal.show === 'function') {
                    // Sempre reatribui o callback para garantir instância correta
                    if (customizer.elements && customizer.elements.saveBtn) {
                        customizer._onSave = (opts) => {
                            const target = currentModuleToCustomize || module;
                            const saved = opts || {};
                            if ('__title' in saved) {
                                try { target.title = String(saved.__title || '').trim(); } catch(e) {}
                                delete saved.__title;
                            }
                            target.custom_options = saved;
                            renderLayoutList();
                        };
                    }
                    customizer.modal.show();
                }
            }
        }
    });


    if (saveTemplateBtn && saveTemplateModal) {
        saveTemplateBtn.addEventListener('click', () => {
            prepareTemplateModal('create', null);
            saveTemplateModal.show();
        });
    }

    if (updateTemplateBtn && saveTemplateModal) {
        updateTemplateBtn.addEventListener('click', () => {
            const info = getSelectedTemplateInfo();
            if (!info) {
                alert('Selecione um template para atualizar.');
                return;
            }
            prepareTemplateModal('update', info.record);
            saveTemplateModal.show();
        });
    }

    if (deleteTemplateBtn) {
        deleteTemplateBtn.addEventListener('click', async () => {
            const info = getSelectedTemplateInfo();
            if (!info) {
                alert('Selecione um template para excluir.');
                return;
            }
            if (!confirm(`Tem certeza que deseja excluir o template "${info.record.name}"?`)) {
                return;
            }
            try {
                const response = await fetch(URLS.delete_template.replace('0', info.id), {
                    method: 'DELETE',
                    headers: withCsrf({ 'Accept': 'application/json' })
                });
                const result = await response.json();
                if (!response.ok || !result.success) {
                    const errorMsg = (result && result.error) ? result.error : 'Erro ao excluir template.';
                    alert(errorMsg);
                    return;
                }
                await refreshSavedTemplates();
                if (Number(activeTemplateId) === Number(info.id)) {
                    activeTemplateId = null;
                }
                logDebug('template.delete.success', { id: info.id });
            } catch (error) {
                logDebug('template.delete.error', { error: String(error) });
                alert('Erro ao excluir template.');
            }
        });
    }

    if (confirmSaveTemplateBtn) {
        confirmSaveTemplateBtn.addEventListener('click', async () => {
            const templateName = templateNameInput ? templateNameInput.value.trim() : '';
            if (!templateName) {
                alert('Informe um nome para o template.');
                return;
            }
            if (!Array.isArray(reportLayout) || reportLayout.length === 0) {
                alert('Adicione ao menos um modulo ao layout antes de salvar.');
                return;
            }
            const payload = {
                name: templateName,
                layout: JSON.stringify(reportLayout)
            };
            if (templateAction === 'update' && templateBeingEditedId) {
                payload.id = templateBeingEditedId;
            }
            try {
                const response = await fetch(URLS.save_template, {
                    method: 'POST',
                    headers: withCsrf({
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }),
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                if (!response.ok || !result.success) {
                    const errorMsg = (result && result.error) ? result.error : 'Falha ao salvar template.';
                    alert(errorMsg);
                    return;
                }
                const savedRecord = result.template;
                const selectedId = (savedRecord && savedRecord.id) ? savedRecord.id : (templateBeingEditedId || null);
                if (saveTemplateModal) {
                    saveTemplateModal.hide();
                }
                await refreshSavedTemplates(selectedId);
                activeTemplateId = selectedId;
                templateAction = 'create';
                templateBeingEditedId = null;
            } catch (error) {
                logDebug('template.save.error', { error: String(error) });
                alert('Erro ao salvar template.');
            }
        });
    }

    // Salvar de cada customizador
    Object.keys(moduleCustomizers).forEach(moduleType => {
        const customizer = moduleCustomizers[moduleType];
        if (customizer.elements && customizer.elements.saveBtn) {
            customizer.elements.saveBtn.addEventListener('click', () => {
                if (!currentModuleToCustomize) return;
                const saved = customizer.save() || {};
                if ('__title' in saved) {
                    try { currentModuleToCustomize.title = String(saved.__title || '').trim(); } catch(e) {}
                    delete saved.__title;
                }
                currentModuleToCustomize.custom_options = saved;
                renderLayoutList();
                customizer.modal.hide();
            });
        }
    });

    // Regras específicas de SLA (já existentes)
    if (moduleCustomizers.sla) {
        const slaElements = moduleCustomizers.sla.elements;
        slaElements.comparePrevMonth.addEventListener('change', () => {
            const isChecked = slaElements.comparePrevMonth.checked;
            slaElements.showPrevSla.disabled = !isChecked;
            slaElements.showImprovement.disabled = !isChecked;
            if (!isChecked) {
                slaElements.showPrevSla.checked = false;
                slaElements.showImprovement.checked = false;
            }
        });
    }

    // Carregar template salvo
    if (loadTemplateBtn) {
        loadTemplateBtn.addEventListener('click', () => {
            const info = getSelectedTemplateInfo();
            if (!info) {
                alert('Selecione um template para carregar.');
                return;
            }
            try {
                const layoutSource = info.record?.layout_json || templateSelector.value || '[]';
                reportLayout = JSON.parse(layoutSource || '[]');
                renderLayoutList();
                activeTemplateId = info.id;
            } catch (e) {
                logDebug('loadTemplateBtn.jsonError', { error: String(e) });
            }
        });
    }

    // Submissão do form é para gerar Relatório
    reportForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (reportLayout.length === 0) {
            statusArea.style.display = 'block';
            statusArea.className = 'alert alert-warning mt-4';
            statusMessage.textContent = 'Atenção! Adicione ao menos um módulo antes de gerar o Relatório.';
            return;
        }

        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Gerando...';
        resetStatusArea();
        statusArea.style.display = 'block';

        const formData = new FormData(reportForm);

        try {
            const response = await fetch(URLS.gerar_relatorio, { method: 'POST', body: formData });
            if (!response.ok) throw new Error(`Erro no servidor: ${response.status} ${response.statusText}`);
            const data = await response.json();
            const taskId = data.task_id;

            if (taskId) {
                activePoll = setInterval(async () => {
                    try {
                        const statusResponse = await fetch(URLS.report_status.replace('0', taskId));
                        if (!statusResponse.ok) throw new Error('Falha ao verificar status');
                        const statusData = await statusResponse.json();

                        statusMessage.textContent = statusData.status || 'Aguardando...';

                        if ((statusData.status || '') === 'Concluido' || !!statusData.file_path) {
                            clearInterval(activePoll);
                            statusMessage.textContent = 'Ok. Relatório gerado com sucesso!';
                            downloadLink.href = URLS.download_report.replace('0', taskId);
                            downloadLink.classList.remove('disabled');
                            generateBtn.disabled = false;
                            generateBtn.innerHTML = '<i class="bi bi-file-earmark-pdf"></i> Gerar Novo Relatório';
                        } else if (statusData.status && statusData.status.startsWith('Erro:')) {
                            clearInterval(activePoll);
                            statusArea.className = 'alert alert-danger mt-4';
                            generateBtn.disabled = false;
                            generateBtn.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Tentar Novamente';
                        }
                    } catch (pollError) {
                        clearInterval(activePoll);
                        logDebug('poll.error', { error: String(pollError) });
                        statusMessage.textContent = `Erro ao consultar status: ${pollError.message}`;
                        statusArea.className = 'alert alert-danger mt-4';
                        generateBtn.disabled = false;
                        generateBtn.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Tentar Novamente';
                    }
                }, 2000);
            } else { throw new Error("Não foi possível iniciar a tarefa."); }

        } catch (error) {
            logDebug('submit.error', { error: String(error) });
            statusMessage.textContent = `Erro: ${error.message}`;
            statusArea.className = 'alert alert-danger mt-4';
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Tentar Novamente';
        }
    });

    // Drag & drop na lista
    new Sortable(layoutList, {
        animation: 150,
        handle: '.bi-grip-vertical',
        onEnd: function (evt) {
            const [movedItem] = reportLayout.splice(evt.oldIndex, 1);
            reportLayout.splice(evt.newIndex, 0, movedItem);
            renderLayoutList();
        }
    });

    // --- INICIALIZAÇÃO ---
    const today = new Date();
    // Define perí­odo padrão: mês corrente
    const y = today.getFullYear();
    const m = today.getMonth() + 1;
    const firstDay = `${y}-${String(m).padStart(2,'0')}-01`;
    const lastDayDate = new Date(y, m, 0);
    const lastDay = `${y}-${String(m).padStart(2,'0')}-${String(lastDayDate.getDate()).padStart(2,'0')}`;
    if (dateFromInput) dateFromInput.value = firstDay;
    if (dateToInput) dateToInput.value = lastDay;
    bootstrapSavedTemplatesFromDom();
    refreshSavedTemplates();
    renderLayoutList();
});

// Fim do app/static/js/gerar_form.js
