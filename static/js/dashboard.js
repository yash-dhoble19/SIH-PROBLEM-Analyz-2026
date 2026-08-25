/**
 * SIH 2026 Intelligence Hub — Main Frontend Application
 * Landing Page first, followed by Explorer & Analytics (Chart.js + 3-tab modal) and Analyze Repo (9-agent pipeline).
 */

const App = (() => {
    // ── State ────────────────────────────────────────
    let allProblems = [];
    let filteredProblems = [];
    let bookmarks = new Set(JSON.parse(localStorage.getItem('sih_bookmarks') || '[]'));
    let currentModalProblem = null;
    let categoryChart = null;
    let themesChart = null;
    let selectedCategory = 'all';
    let viewMode = 'grid';
    let isBookmarkOnly = false;
    let currentJobId = null;
    let pollInterval = null;

    // ── API Helper ───────────────────────────────────
    async function api(url, opts = {}) {
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...opts.headers },
            ...opts
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        const ct = res.headers.get('content-type') || '';
        return ct.includes('application/json') ? res.json() : res.text();
    }

    // ── Navigation ───────────────────────────────────
    function navigate(viewName) {
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.view === viewName);
        });
        document.querySelectorAll('.app-view').forEach(view => {
            view.classList.toggle('active', view.id === `view-${viewName}`);
        });

        window.scrollTo({ top: 0, behavior: 'smooth' });

        // If navigating to explorer and charts haven't rendered, render them
        if (viewName === 'explorer' && allProblems.length && (!categoryChart || !themesChart)) {
            loadStats();
        }
    }

    // ── Init ─────────────────────────────────────────
    async function init() {
        // Wire Navigation Tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                navigate(tab.dataset.view);
            });
        });

        // Wire Search Input
        const searchInput = document.getElementById('main-search-input');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', () => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => filterAndRender(), 180);
            });
        }

        // Wire Category Pills
        document.querySelectorAll('.pill-btn').forEach(pill => {
            pill.addEventListener('click', () => {
                document.querySelectorAll('.pill-btn').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                selectedCategory = pill.dataset.cat;
                filterAndRender();
            });
        });

        // Wire Dropdowns
        document.getElementById('theme-dropdown')?.addEventListener('change', () => filterAndRender());
        document.getElementById('org-dropdown')?.addEventListener('change', () => filterAndRender());

        // Close modal on escape
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') {
                closeModal();
                closeRatingModal();
            }
        });

        // Load data in background & log visit
        await Promise.all([loadStats(), loadFilters(), loadProblems(), logVisitor(), loadRatingsSummary()]);
    }

    // ── Stats & Charts ───────────────────────────────
    async function loadStats() {
        try {
            const stats = await api('/api/stats');
            const totalEl = document.getElementById('kpi-total');
            if (totalEl) totalEl.textContent = stats.total_records || 226;
            const softEl = document.getElementById('kpi-software');
            if (softEl) softEl.textContent = stats.software_count || 172;
            const hardEl = document.getElementById('kpi-hardware');
            if (hardEl) hardEl.textContent = stats.hardware_count || 54;
            const themeEl = document.getElementById('kpi-themes');
            if (themeEl) themeEl.textContent = Object.keys(stats.all_themes || {}).length || 18;
            const orgEl = document.getElementById('kpi-orgs');
            if (orgEl) orgEl.textContent = Object.keys(stats.all_organizations || {}).length || 30;

            renderCategoryChart(stats.software_count || 172, stats.hardware_count || 54);
            renderThemesChart(stats.top_themes || []);
        } catch (e) {
            console.error('Stats loading error:', e);
        }
    }

    function renderCategoryChart(software, hardware) {
        const ctx = document.getElementById('categoryChart')?.getContext('2d');
        if (!ctx) return;
        if (categoryChart) categoryChart.destroy();

        categoryChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Software', 'Hardware'],
                datasets: [{
                    data: [software, hardware],
                    backgroundColor: ['#06b6d4', '#f97316'],
                    borderWidth: 0,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '72%',
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: '#94a3b8', font: { family: 'Inter', size: 11, weight: '600' } }
                    }
                }
            }
        });
    }

    function renderThemesChart(topThemes) {
        const ctx = document.getElementById('themesChart')?.getContext('2d');
        if (!ctx) return;
        if (themesChart) themesChart.destroy();

        const labels = topThemes.slice(0, 8).map(t => t.theme);
        const counts = topThemes.slice(0, 8).map(t => t.count);

        themesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Statements',
                    data: counts,
                    backgroundColor: '#8b5cf6',
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#64748b', font: { family: 'Inter', size: 10 } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: {
                            color: '#94a3b8',
                            font: { family: 'Inter', size: 11, weight: '500' },
                            callback: function(val, index) {
                                const label = labels[index] || '';
                                return label.length > 20 ? label.substr(0, 18) + '...' : label;
                            }
                        }
                    }
                }
            }
        });
    }

    // ── Filters ──────────────────────────────────────
    async function loadFilters() {
        try {
            const filters = await api('/api/filters');
            const themeSel = document.getElementById('theme-dropdown');
            const orgSel = document.getElementById('org-dropdown');

            if (themeSel && filters.themes) {
                themeSel.innerHTML = `<option value="">All Themes (${filters.themes.length})</option>` +
                    filters.themes.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
            }

            if (orgSel && filters.organizations) {
                orgSel.innerHTML = `<option value="">All Ministries / Orgs (${filters.organizations.length})</option>` +
                    filters.organizations.map(o => `<option value="${escapeHtml(o)}">${escapeHtml(o)}</option>`).join('');
            }
        } catch (e) {
            console.error('Filter options load error:', e);
        }
    }

    // ── Problems ─────────────────────────────────────
    async function loadProblems() {
        try {
            const res = await api('/api/problems?limit=1000');
            allProblems = res.data || [];
            filteredProblems = [...allProblems];
            renderCards();
        } catch (e) {
            const cont = document.getElementById('problems-container');
            if (cont) cont.innerHTML = '<div style="color:#f87171;padding:2rem;text-align:center;">Failed to load problem statements.</div>';
        }
    }

    function filterAndRender() {
        const q = (document.getElementById('main-search-input')?.value || '').toLowerCase().trim();
        const theme = document.getElementById('theme-dropdown')?.value || '';
        const org = document.getElementById('org-dropdown')?.value || '';

        filteredProblems = allProblems.filter(p => {
            if (selectedCategory !== 'all' && p.category?.toLowerCase() !== selectedCategory.toLowerCase()) return false;
            if (theme && p.theme !== theme) return false;
            if (org && p.organization !== org) return false;
            if (isBookmarkOnly && !bookmarks.has(p.problem_statement_id)) return false;

            if (q) {
                const combined = `${p.problem_statement_id} ${p.title} ${p.organization} ${p.department || ''} ${p.theme} ${p.description} ${p.expected_solution || ''} ${p.background || ''}`.toLowerCase();
                if (!combined.includes(q)) return false;
            }
            return true;
        });

        renderCards();
    }

    function renderCards() {
        const container = document.getElementById('problems-container');
        if (!container) return;

        const countEl = document.getElementById('visible-count');
        if (countEl) countEl.textContent = filteredProblems.length;

        if (!filteredProblems.length) {
            container.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:3rem;color:#64748b;">No matching problem statements found.</div>';
            return;
        }

        container.className = viewMode === 'grid' ? 'cards-grid' : 'cards-table-view';

        container.innerHTML = filteredProblems.map(p => {
            const isBookmarked = bookmarks.has(p.problem_statement_id);
            const catClass = p.category?.toLowerCase() === 'software' ? 'cat-software' : 'cat-hardware';

            return `
                <div class="ps-card" onclick="App.openModal('${p.problem_statement_id}')">
                    <div class="ps-card-top">
                        <span class="ps-id-badge">${p.problem_statement_id}</span>
                        <span class="ps-cat-badge ${catClass}">${p.category}</span>
                    </div>
                    <div class="ps-card-title">${escapeHtml(p.title)}</div>
                    <div class="ps-card-org">
                        <span>🏛️</span> ${escapeHtml(p.organization)}
                    </div>
                    <div class="ps-card-desc">
                        ${escapeHtml(p.description)}
                    </div>
                    <div class="ps-card-footer">
                        <span class="ps-theme-tag">🏷️ ${escapeHtml(p.theme)}</span>
                        <div class="ps-card-actions" onclick="event.stopPropagation()">
                            <button class="btn-star-bookmark ${isBookmarked ? 'bookmarked' : ''}" 
                                onclick="App.toggleBookmark('${p.problem_statement_id}')" 
                                title="${isBookmarked ? 'Remove Bookmark' : 'Add Bookmark'}">
                                ${isBookmarked ? '★' : '☆'}
                            </button>
                            <button class="btn-card-details" onclick="App.openModal('${p.problem_statement_id}')">
                                Details &rarr;
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function setViewMode(mode) {
        viewMode = mode;
        document.getElementById('btn-grid-view')?.classList.toggle('active', mode === 'grid');
        document.getElementById('btn-table-view')?.classList.toggle('active', mode === 'table');
        renderCards();
    }

    function resetFilters() {
        const searchEl = document.getElementById('main-search-input');
        if (searchEl) searchEl.value = '';
        const themeEl = document.getElementById('theme-dropdown');
        if (themeEl) themeEl.value = '';
        const orgEl = document.getElementById('org-dropdown');
        if (orgEl) orgEl.value = '';
        selectedCategory = 'all';
        isBookmarkOnly = false;
        document.querySelectorAll('.pill-btn').forEach(p => p.classList.toggle('active', p.dataset.cat === 'all'));
        document.getElementById('btn-bookmark-filter')?.classList.remove('active');
        filterAndRender();
    }

    function toggleBookmark(psId) {
        if (bookmarks.has(psId)) {
            bookmarks.delete(psId);
        } else {
            bookmarks.add(psId);
        }
        localStorage.setItem('sih_bookmarks', JSON.stringify([...bookmarks]));
        renderCards();
    }

    function toggleBookmarkFilter() {
        isBookmarkOnly = !isBookmarkOnly;
        document.getElementById('btn-bookmark-filter')?.classList.toggle('active', isBookmarkOnly);
        filterAndRender();
    }

    // ═══════════════════════════════════════════════════
    // 3-TAB MODAL LOGIC
    // ═══════════════════════════════════════════════════
    function openModal(psId) {
        const p = allProblems.find(x => x.problem_statement_id === psId);
        if (!p) return;
        currentModalProblem = p;

        // Populate Top Header Badges & Title
        document.getElementById('m-id-badge').textContent = p.problem_statement_id;
        const catBadge = document.getElementById('m-cat-badge');
        catBadge.textContent = p.category.toUpperCase();
        catBadge.className = `ps-cat-badge ${p.category?.toLowerCase() === 'software' ? 'cat-software' : 'cat-hardware'}`;
        document.getElementById('m-title').textContent = p.title;

        // Tab 1: Complete Details
        document.getElementById('m-org').textContent = p.organization || '—';
        document.getElementById('m-dept').textContent = p.department || p.organization || '—';
        document.getElementById('m-theme').textContent = p.theme || '—';
        document.getElementById('m-submissions').textContent = p.submitted_ideas_count || '0/500';
        document.getElementById('m-deadline').textContent = p.deadline_for_idea_submission || '20 September 2026';
        document.getElementById('m-dataset').innerHTML = p.dataset_link ? `<a href="${p.dataset_link}" target="_blank" style="color:#38bdf8;">Link</a>` : 'None';

        // Background
        const bgSec = document.getElementById('m-bg-section');
        if (p.background && p.background.trim()) {
            bgSec.style.display = 'block';
            document.getElementById('m-background').textContent = p.background;
        } else {
            bgSec.style.display = 'none';
        }

        // Description
        document.getElementById('m-description').textContent = p.description;

        // Solution
        const solSec = document.getElementById('m-sol-section');
        if (p.expected_solution && p.expected_solution.trim()) {
            solSec.style.display = 'block';
            document.getElementById('m-solution').textContent = p.expected_solution;
        } else {
            solSec.style.display = 'none';
        }

        // Links / Youtube / Contact
        const linksSec = document.getElementById('m-links-section');
        let linksHtml = '';
        if (p.youtube_link) linksHtml += `<div><strong>YouTube:</strong> <a href="${p.youtube_link}" target="_blank" style="color:#38bdf8;">${p.youtube_link}</a></div>`;
        if (p.contact_info) linksHtml += `<div><strong>Contact:</strong> ${escapeHtml(p.contact_info)}</div>`;
        if (linksHtml) {
            linksSec.style.display = 'block';
            document.getElementById('m-links').innerHTML = linksHtml;
        } else {
            linksSec.style.display = 'none';
        }

        // Tab 2: AI / RAG Prompt View
        document.getElementById('m-rag-text').textContent = p.search_text || generateRAGPromptText(p);

        // Tab 3: Raw JSON Data
        document.getElementById('m-json-text').textContent = JSON.stringify(p, null, 2);

        // Reset to first tab
        switchModalTab('details');

        document.getElementById('problem-detail-modal').style.display = 'flex';
    }

    function closeModal() {
        const modal = document.getElementById('problem-detail-modal');
        if (modal) modal.style.display = 'none';
    }

    function switchModalTab(tabName) {
        document.querySelectorAll('.modal-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        document.querySelectorAll('.modal-tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `tab-${tabName}`);
        });
    }

    function generateRAGPromptText(p) {
        return `Problem Statement ID: ${p.problem_statement_id}
Title: ${p.title}
Category: ${p.category}
Theme: ${p.theme}
Organization: ${p.organization}
Department: ${p.department || 'N/A'}

Background:
${p.background || 'N/A'}

Description:
${p.description}

Expected Solution:
${p.expected_solution || 'N/A'}`;
    }

    function copyCurrentPSID() {
        if (!currentModalProblem) return;
        copyToClipboard(currentModalProblem.problem_statement_id, 'PS ID copied!');
    }

    function copyRAGPrompt() {
        if (!currentModalProblem) return;
        const text = currentModalProblem.search_text || generateRAGPromptText(currentModalProblem);
        copyToClipboard(text, '✨ AI / RAG Prompt Copied!');
    }

    function analyzeFromModal() {
        if (!currentModalProblem) return;
        closeModal();
        navigate('analyze');
    }

    function copyToClipboard(text, successMsg) {
        navigator.clipboard.writeText(text).then(() => {
            const notify = document.createElement('div');
            notify.textContent = successMsg || 'Copied to clipboard!';
            notify.style.cssText = 'position:fixed;bottom:24px;right:24px;background:#8b5cf6;color:#fff;padding:10px 18px;border-radius:8px;font-size:0.85rem;font-weight:700;z-index:9999;box-shadow:0 8px 30px rgba(0,0,0,0.5);animation:fadeIn 0.2s ease;';
            document.body.appendChild(notify);
            setTimeout(() => notify.remove(), 2200);
        });
    }

    // ── Repository Analysis (9-Agent Pipeline) ───────
    async function startAnalysis() {
        const input = document.getElementById('repo-url-input');
        const errBanner = document.getElementById('repo-error-msg');
        const url = input?.value?.trim();
        errBanner.style.display = 'none';

        if (!url) {
            errBanner.textContent = 'Please enter a valid GitHub repository URL.';
            errBanner.style.display = 'block';
            return;
        }

        const stepperPanel = document.getElementById('analysis-stepper-panel');
        const resultsPanel = document.getElementById('repo-results-panel');
        const deepPanel = document.getElementById('match-deep-panel');

        stepperPanel.style.display = 'block';
        resultsPanel.style.display = 'none';
        deepPanel.style.display = 'none';

        document.getElementById('stepper-bar').style.width = '5%';
        document.getElementById('stepper-status').textContent = 'Queuing repository analysis pipeline...';
        document.getElementById('agent-runs-list').innerHTML = '';
        document.getElementById('btn-submit-analyze').disabled = true;

        try {
            const data = await api('/api/repositories/analyze', {
                method: 'POST',
                body: JSON.stringify({ github_url: url })
            });
            currentJobId = data.job_id;
            pollAnalysisProgress();
        } catch (e) {
            errBanner.textContent = e.message;
            errBanner.style.display = 'block';
            stepperPanel.style.display = 'none';
            document.getElementById('btn-submit-analyze').disabled = false;
        }
    }

    function pollAnalysisProgress() {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(async () => {
            try {
                const job = await api(`/api/jobs/${currentJobId}`);
                document.getElementById('stepper-bar').style.width = `${job.progress_pct}%`;
                document.getElementById('stepper-status').textContent = job.current_step;

                if (job.status === 'COMPLETED') {
                    clearInterval(pollInterval);
                    document.getElementById('btn-submit-analyze').disabled = false;
                    await renderAnalysisOverview(job.analysis_id);
                } else if (job.status === 'FAILED') {
                    clearInterval(pollInterval);
                    document.getElementById('stepper-status').textContent = `Failed: ${job.error || 'Unknown error'}`;
                    document.getElementById('btn-submit-analyze').disabled = false;
                }
            } catch (e) {
                clearInterval(pollInterval);
                document.getElementById('btn-submit-analyze').disabled = false;
            }
        }, 1800);
    }

    async function renderAnalysisOverview(analysisId) {
        const resultsPanel = document.getElementById('repo-results-panel');
        try {
            const data = await api(`/api/analyses/${analysisId}`);
            
            // Agent logs
            try {
                const agents = await api(`/api/analyses/${analysisId}/agents`);
                document.getElementById('agent-runs-list').innerHTML = agents.map(a => `
                    <div class="agent-step-item">
                        <span class="agent-dot ${a.status?.toLowerCase()}"></span>
                        <span class="agent-step-name">${escapeHtml(a.agent_name)}</span>
                        <span class="agent-step-dur">${a.duration_ms ? `${a.duration_ms}ms` : '—'}</span>
                    </div>
                `).join('');
            } catch (_) {}

            let html = `
                <div style="background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);padding:1.5rem;margin-top:1.5rem;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
                        <h3 style="font-size:1.2rem;font-weight:800;color:#fff;">${escapeHtml(data.repo_name)}</h3>
                        <span class="ps-id-badge">${escapeHtml(data.project_type || 'Software Application')}</span>
                    </div>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:1rem;">
                        ${(data.detected_languages || []).map(l => `<span class="ps-cat-badge cat-software">${l}</span>`).join('')}
                        ${data.backend_framework ? `<span class="ps-cat-badge cat-software">${data.backend_framework}</span>` : ''}
                        ${data.frontend_framework ? `<span class="ps-cat-badge cat-software">${data.frontend_framework}</span>` : ''}
                        ${data.database_tech ? `<span class="ps-cat-badge cat-hardware">${data.database_tech}</span>` : ''}
                    </div>
                    <p style="font-size:0.875rem;color:var(--text-secondary);line-height:1.6;margin-bottom:1.25rem;">${escapeHtml(data.project_summary || '')}</p>

                    ${data.is_low_confidence ? `
                        <div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);color:#fbbf24;padding:10px 14px;border-radius:var(--radius-md);margin-bottom:1.25rem;font-size:0.8rem;">
                            ⚠️ <strong>Grounding Caution:</strong> ${escapeHtml(data.confidence_warning || 'Some capabilities could not be verified in the codebase.')}
                        </div>
                    ` : ''}

                    ${data.embedding_fallback_active ? `
                        <div style="background:rgba(251,146,60,0.12);border:1px solid rgba(251,146,60,0.4);color:#fdba74;padding:12px 16px;border-radius:var(--radius-md);margin-bottom:1.25rem;font-size:0.82rem;display:flex;align-items:flex-start;gap:10px;">
                            <span style="font-size:1.3rem;line-height:1;">🔌</span>
                            <div>
                                <strong style="color:#fb923c;">Embedding Fallback Active — Semantic Scores Degraded</strong><br/>
                                <span style="color:#fdba74;">No real embedding API key is configured. Semantic similarity scores are computed using a deterministic local hash instead of a neural embedding model. Match scores may be less accurate. Configure an OpenAI or Google AI API key in <code style="background:rgba(0,0,0,0.3);padding:2px 5px;border-radius:3px;">.env</code> to enable full-fidelity scoring.</span>
                            </div>
                        </div>
                    ` : ''}
                    ${data.grounded_capabilities && data.grounded_capabilities.length > 0 ? `
                        <div style="margin-bottom:1.5rem;">
                            <div style="font-size:0.75rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Verified Codebase Capabilities (Citations)</div>
                            <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(280px, 1fr));gap:8px;">
                                ${data.grounded_capabilities.map(c => `
                                    <div style="padding:8px 12px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:6px;display:flex;flex-direction:column;gap:4px;">
                                        <span style="color:#e2e8f0;font-size:0.825rem;font-weight:600;">✓ ${escapeHtml(c.capability)}</span>
                                        <span style="color:var(--text-muted);font-size:0.7rem;">📍 ${escapeHtml(c.source)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <h4 style="font-size:1rem;font-weight:700;color:var(--text-cyan);margin-bottom:1rem;">Top SIH 2026 Matches (${(data.matches || []).length})</h4>
                    <div style="display:flex;flex-direction:column;gap:12px;">
                        ${(data.matches || []).map(m => {
                            const scoreClass = m.overall_match_score >= 80 ? 'score-high' : (m.overall_match_score >= 60 ? 'score-medium' : 'score-low');
                            return `
                                <div class="ps-card" onclick="App.showDeepMatch('${m.id}')" style="cursor:pointer;">
                                    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:14px;">
                                        <div style="flex:1;">
                                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                                                <span class="ps-id-badge">${m.problem_statement_id}</span>
                                                <span class="ps-cat-badge ${m.category?.toLowerCase() === 'software' ? 'cat-software' : 'cat-hardware'}">${m.category}</span>
                                                <span style="font-size:0.75rem;color:var(--text-muted);">${escapeHtml(m.theme)}</span>
                                            </div>
                                            <div style="font-size:0.95rem;font-weight:700;color:#fff;margin-bottom:6px;">${escapeHtml(m.title)}</div>
                                            <div style="display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 8px;">
                                                <span class="ps-cat-badge" style="background:rgba(168,85,247,0.15);color:#c084fc;border:1px solid rgba(168,85,247,0.3);">🎯 Aim/Intent: ${Math.round(m.aim_alignment_score || 0)}%</span>
                                                <span class="ps-cat-badge cat-software">Semantic: ${Math.round(m.semantic_similarity)}%</span>
                                                <span class="ps-cat-badge cat-hardware">Feature: ${Math.round(m.feature_alignment)}%</span>
                                                <span class="ps-cat-badge" style="background:rgba(6,182,212,0.12);color:#22d3ee;border:1px solid rgba(6,182,212,0.3);">Domain: ${Math.round(m.domain_alignment)}%</span>
                                            </div>
                                            <p style="font-size:0.825rem;color:var(--text-secondary);">${escapeHtml(m.match_reasoning || '')}</p>
                                        </div>
                                        <div class="score-badge-circle ${scoreClass}">
                                            ${Math.round(m.overall_match_score)}%
                                        </div>
                                    </div>
                                    <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.05);display:flex;justify-content:flex-end;">
                                        <button class="btn-glow-purple" style="padding:6px 14px;font-size:0.75rem;">
                                            View Gap Matrix &amp; Prompts &rarr;
                                        </button>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;

            resultsPanel.innerHTML = html;
            resultsPanel.style.display = 'block';
        } catch (e) {
            resultsPanel.innerHTML = `<div style="color:#f87171;padding:2rem;">Failed to load analysis results: ${escapeHtml(e.message)}</div>`;
            resultsPanel.style.display = 'block';
        }
    }

    async function showDeepMatch(matchId) {
        const deepPanel = document.getElementById('match-deep-panel');
        const resultsPanel = document.getElementById('repo-results-panel');
        resultsPanel.style.display = 'none';
        deepPanel.style.display = 'block';
        deepPanel.innerHTML = '<div style="text-align:center;padding:3rem;color:var(--text-secondary);">Generating deep gap analysis, phased roadmap, and coding prompts...</div>';

        try {
            const d = await api(`/api/matches/${matchId}`);
            const gap = d.gap_analysis;
            const plan = d.implementation_plan;

            let html = `
                <button onclick="App.backToMatches()" class="action-btn" style="margin-bottom:1.5rem;">
                    &larr; Back to Top Matches
                </button>

                <div style="background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);padding:1.75rem;margin-bottom:1.5rem;">
                    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:1rem;">
                        <div>
                            <span class="ps-id-badge">${d.problem_statement.id}</span>
                            <h2 style="font-size:1.3rem;font-weight:800;color:#fff;margin-top:8px;">${escapeHtml(d.problem_statement.title)}</h2>
                            <div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px;">${escapeHtml(d.problem_statement.organization)} &middot; ${escapeHtml(d.problem_statement.theme)}</div>
                        </div>
                        <div class="score-badge-circle ${d.scores.overall >= 80 ? 'score-high' : 'score-medium'}">
                            ${Math.round(d.scores.overall)}%
                        </div>
                    </div>

                    <!-- 6-Factor Breakdown Grid -->
                    <div style="display:grid;grid-template-columns:repeat(6, 1fr);gap:8px;background:var(--bg-input);padding:12px;border-radius:var(--radius-md);margin:1rem 0;">
                        <div style="text-align:center;"><div style="font-size:0.65rem;color:#c084fc;font-weight:700;">🎯 AIM / INTENT (30%)</div><div style="font-size:1.1rem;font-weight:800;color:#fff;margin-top:2px;">${Math.round(d.scores.aim_alignment || 0)}%</div></div>
                        <div style="text-align:center;"><div style="font-size:0.65rem;color:var(--text-muted);font-weight:700;">SEMANTIC (20%)</div><div style="font-size:1.1rem;font-weight:800;color:#fff;margin-top:2px;">${Math.round(d.scores.semantic)}%</div></div>
                        <div style="text-align:center;"><div style="font-size:0.65rem;color:var(--text-muted);font-weight:700;">FEATURE (20%)</div><div style="font-size:1.1rem;font-weight:800;color:#fff;margin-top:2px;">${Math.round(d.scores.feature)}%</div></div>
                        <div style="text-align:center;"><div style="font-size:0.65rem;color:var(--text-muted);font-weight:700;">DOMAIN (10%)</div><div style="font-size:1.1rem;font-weight:800;color:#fff;margin-top:2px;">${Math.round(d.scores.domain)}%</div></div>
                        <div style="text-align:center;"><div style="font-size:0.65rem;color:var(--text-muted);font-weight:700;">TECH (10%)</div><div style="font-size:1.1rem;font-weight:800;color:#fff;margin-top:2px;">${Math.round(d.scores.tech)}%</div></div>
                        <div style="text-align:center;"><div style="font-size:0.65rem;color:var(--text-muted);font-weight:700;">SOLUTION (10%)</div><div style="font-size:1.1rem;font-weight:800;color:#fff;margin-top:2px;">${Math.round(d.scores.solution)}%</div></div>
                    </div>

                    <p style="font-size:0.875rem;color:var(--text-secondary);line-height:1.6;">${escapeHtml(d.scores.reasoning || '')}</p>
                </div>

                <!-- Gap Matrix -->
                <div style="background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);padding:1.5rem;margin-bottom:1.5rem;">
                    <h3 style="font-size:1.05rem;font-weight:700;color:var(--text-cyan);margin-bottom:0.4rem;">
                        📊 Requirement Gap Matrix (Reusability: ${gap.reusability_score}%)
                    </h3>
                    <p style="font-size:0.825rem;color:var(--text-secondary);margin-bottom:1rem;">${escapeHtml(gap.summary_findings || '')}</p>
                    <table class="gap-matrix-table">
                        <thead>
                            <tr>
                                <th>Requirement</th>
                                <th>Your Project</th>
                                <th>Status</th>
                                <th>Reason</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${(gap.requirement_matrix || []).map(r => `
                                <tr>
                                    <td><strong>${escapeHtml(r.requirement)}</strong></td>
                                    <td>${escapeHtml(r.current_project)}</td>
                                    <td><span class="status-pill status-${r.status}">${r.status}</span></td>
                                    <td>${escapeHtml(r.reason)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>

                <!-- Pivot Advisor: Transform Your Project to Match This -->
                ${d.pivot_advisor ? `
                <div style="background:linear-gradient(145deg, rgba(168,85,247,0.08), rgba(6,182,212,0.08));border:1px solid rgba(168,85,247,0.35);border-radius:var(--radius-lg);padding:1.5rem;margin-bottom:1.5rem;">
                    <div style="display:flex;align-items:center;justify-content:space-between;cursor:pointer;" onclick="App.togglePivotAdvisorCard()">
                        <div style="display:flex;align-items:center;gap:10px;">
                            <span style="font-size:1.4rem;">🔄</span>
                            <div>
                                <h3 style="font-size:1.1rem;font-weight:800;color:#c084fc;margin:0;">
                                    Transform Your Project to Match This
                                </h3>
                                <div style="font-size:0.8rem;color:var(--text-muted);margin-top:2px;">
                                    Actionable Pivot Strategy &middot; Reusability: ${Math.round(d.pivot_advisor.reusability_score)}% &middot; Domain Alignment: ${Math.round(d.pivot_advisor.domain_alignment)}%
                                </div>
                            </div>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span class="ps-cat-badge" style="background:rgba(168,85,247,0.2);color:#d8b4fe;border:1px solid rgba(168,85,247,0.4);">
                                Pivot Strategy
                            </span>
                            <span id="pivot-toggle-icon" style="font-size:1.1rem;color:var(--text-muted);transition:transform 0.2s;">▼</span>
                        </div>
                    </div>

                    <div id="pivot-advisor-body" style="display:block;margin-top:1.25rem;padding-top:1.25rem;border-top:1px solid rgba(255,255,255,0.08);">
                        <p style="font-size:0.875rem;color:var(--text-secondary);line-height:1.6;margin-bottom:1.25rem;background:rgba(0,0,0,0.25);padding:10px 14px;border-radius:var(--radius-md);border-left:3px solid #c084fc;">
                            ${escapeHtml(d.pivot_advisor.transformation_summary || '')}
                        </p>

                        <!-- Two Columns: What You Can Reuse vs. What You'd Need to Add -->
                        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));gap:1.25rem;margin-bottom:1.5rem;">
                            <!-- Column 1: What You Can Reuse -->
                            <div style="background:var(--bg-input);border:1px solid rgba(34,197,94,0.25);border-radius:var(--radius-md);padding:1.1rem;">
                                <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
                                    <span style="color:#4ade80;font-size:1.1rem;">✅</span>
                                    <h4 style="font-size:0.95rem;font-weight:700;color:#4ade80;margin:0;">What You Can Reuse</h4>
                                </div>
                                <div style="display:flex;flex-direction:column;gap:10px;">
                                    ${(d.pivot_advisor.reused_foundations || []).map(rf => `
                                        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:var(--radius-sm);padding:10px;">
                                            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
                                                <strong style="font-size:0.85rem;color:#fff;">${escapeHtml(rf.capability)}</strong>
                                                <span class="status-pill status-MATCH" style="font-size:0.65rem;padding:2px 6px;">REUSE</span>
                                            </div>
                                            <div style="font-size:0.775rem;color:var(--text-muted);margin-bottom:4px;">
                                                <code>${escapeHtml(rf.source_evidence)}</code>
                                            </div>
                                            <div style="font-size:0.8rem;color:var(--text-secondary);line-height:1.4;">
                                                ${escapeHtml(rf.reuse_mechanism)}
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>

                            <!-- Column 2: What You'd Need to Add -->
                            <div style="background:var(--bg-input);border:1px solid rgba(249,115,22,0.25);border-radius:var(--radius-md);padding:1.1rem;">
                                <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
                                    <span style="color:#fb923c;font-size:1.1rem;">⚡</span>
                                    <h4 style="font-size:0.95rem;font-weight:700;color:#fb923c;margin:0;">What You'd Need to Add</h4>
                                </div>
                                <div style="display:flex;flex-direction:column;gap:10px;">
                                    ${(d.pivot_advisor.required_additions || []).map(ra => `
                                        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:var(--radius-sm);padding:10px;">
                                            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
                                                <strong style="font-size:0.85rem;color:#fff;">${escapeHtml(ra.feature)}</strong>
                                                <span class="status-pill status-${ra.priority.includes('P0') ? 'MISSING' : 'PARTIAL'}" style="font-size:0.65rem;padding:2px 6px;">${escapeHtml(ra.priority)} &middot; ${escapeHtml(ra.effort_estimate)}</span>
                                            </div>
                                            <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:4px;">
                                                <strong>Why:</strong> ${escapeHtml(ra.why_needed)}
                                            </div>
                                            <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:4px;">
                                                <strong>Approach:</strong> ${escapeHtml(ra.build_approach)}
                                            </div>
                                            <div style="font-size:0.75rem;color:var(--text-muted);">
                                                Target: <code>${escapeHtml(ra.integration_target)}</code>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </div>

                        <!-- Copy-Paste Transformation Prompt -->
                        <div style="background:var(--bg-terminal);border:1px solid rgba(168,85,247,0.3);border-radius:var(--radius-md);padding:1.2rem;">
                            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                                <div style="display:flex;align-items:center;gap:8px;">
                                    <span class="ps-id-badge" style="background:#7e22ce;">PIVOT PROMPT</span>
                                    <span style="font-size:0.9rem;font-weight:700;color:#fff;">Copy-Paste Transformation Prompt (Cursor / Claude Code / Antigravity)</span>
                                </div>
                                <button class="btn-glow-purple" style="padding:5px 14px;font-size:0.75rem;" onclick="App.copyPromptText('pivot-advisor-prompt-text')">
                                    📋 Copy Pivot Prompt
                                </button>
                            </div>
                            <pre id="pivot-advisor-prompt-text" style="font-family:var(--font-mono);font-size:0.78rem;color:#cbd5e1;white-space:pre-wrap;max-height:280px;overflow-y:auto;line-height:1.6;">${escapeHtml(d.pivot_advisor.copy_paste_prompt || '')}</pre>
                        </div>
                    </div>
                </div>
                ` : ''}

                <!-- Phased Implementation Plan -->
                <div style="background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);padding:1.5rem;margin-bottom:1.5rem;">
                    <h3 style="font-size:1.05rem;font-weight:700;color:var(--text-purple);margin-bottom:0.4rem;">
                        🗺️ Phased Implementation Roadmap
                    </h3>
                    <p style="font-size:0.825rem;color:var(--text-secondary);margin-bottom:1.25rem;">
                        Effort Estimate: <strong>${escapeHtml(plan.estimated_effort || '2-3 days')}</strong> &middot; ${escapeHtml(plan.architecture_overview || '')}
                    </p>
                    <div style="display:flex;flex-direction:column;gap:12px;">
                        ${(plan.phases || []).map(ph => `
                            <div style="background:var(--bg-input);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:1.1rem;">
                                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                                    <h4 style="font-size:0.925rem;font-weight:700;color:#fff;">${escapeHtml(ph.title)}</h4>
                                    <span class="status-pill status-${ph.complexity === 'High' ? 'MISSING' : (ph.complexity === 'Medium' ? 'PARTIAL' : 'MATCH')}">${ph.complexity} Complexity</span>
                                </div>
                                <p style="font-size:0.825rem;color:var(--text-secondary);margin-bottom:4px;"><strong>Why:</strong> ${escapeHtml(ph.why)}</p>
                                <p style="font-size:0.825rem;color:var(--text-secondary);margin-bottom:4px;"><strong>Required Changes:</strong> ${escapeHtml(ph.required_changes)}</p>
                                <div style="font-size:0.8rem;color:var(--text-muted);">
                                    <span>Modify: ${(ph.files_to_modify || []).map(f => `<code>${f}</code>`).join(', ') || '—'}</span> &middot; 
                                    <span>Create: ${(ph.files_to_create || []).map(f => `<code>${f}</code>`).join(', ') || '—'}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Modular AI Coding Prompts -->
                <div style="background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);padding:1.5rem;margin-bottom:1.5rem;">
                    <h3 style="font-size:1.05rem;font-weight:700;color:#facc15;margin-bottom:0.4rem;">
                        🤖 Modular AI Coding Prompts (Cursor / Claude Code / Antigravity)
                    </h3>
                    <p style="font-size:0.825rem;color:var(--text-secondary);margin-bottom:1.25rem;">
                        Copy these exact modular prompts directly into your AI coding assistant to implement the required capabilities.
                    </p>
                    <div style="display:flex;flex-direction:column;gap:14px;">
                        ${(d.prompts || []).map((p, idx) => `
                            <div style="background:var(--bg-terminal);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:1.2rem;">
                                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                                    <div style="display:flex;align-items:center;gap:8px;">
                                        <span class="ps-id-badge">${p.category}</span>
                                        <span style="font-size:0.9rem;font-weight:700;color:#fff;">${escapeHtml(p.title)}</span>
                                    </div>
                                    <button class="btn-glow-purple" style="padding:5px 12px;font-size:0.75rem;" onclick="App.copyPromptText('prompt-code-${idx}')">
                                        📋 Copy Prompt
                                    </button>
                                </div>
                                <pre id="prompt-code-${idx}" style="font-family:var(--font-mono);font-size:0.78rem;color:#94a3b8;white-space:pre-wrap;max-height:260px;overflow-y:auto;line-height:1.6;">${escapeHtml(p.prompt_text)}</pre>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Export Report -->
                <div style="display:flex;gap:10px;margin-bottom:2rem;">
                    <a href="/api/reports/${matchId}/export?format=markdown" target="_blank" class="action-btn">
                        📥 Export Markdown Report
                    </a>
                    <a href="/api/reports/${matchId}/export?format=json" target="_blank" class="action-btn">
                        📥 Export JSON Data
                    </a>
                </div>
            `;

            deepPanel.innerHTML = html;
        } catch (e) {
            deepPanel.innerHTML = `<div style="color:#f87171;padding:2rem;">Failed to load match detail: ${escapeHtml(e.message)}</div>`;
        }
    }

    function togglePivotAdvisorCard() {
        const body = document.getElementById('pivot-advisor-body');
        const icon = document.getElementById('pivot-toggle-icon');
        if (!body) return;
        if (body.style.display === 'none') {
            body.style.display = 'block';
            if (icon) icon.textContent = '▼';
        } else {
            body.style.display = 'none';
            if (icon) icon.textContent = '▶';
        }
    }

    function backToMatches() {
        document.getElementById('match-deep-panel').style.display = 'none';
        document.getElementById('repo-results-panel').style.display = 'block';
    }

    function copyPromptText(elementId) {
        const text = document.getElementById(elementId)?.textContent || '';
        copyToClipboard(text, '✨ AI Prompt Copied to Clipboard!');
    }

    // ── Export Functions ──────────────────────────────
    function exportJSON() {
        if (!allProblems.length) return;
        const blob = new Blob([JSON.stringify(allProblems, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sih_2026_problems_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    function exportCSV() {
        if (!allProblems.length) return;
        const headers = ['problem_statement_id', 'title', 'organization', 'department', 'category', 'theme', 'description', 'expected_solution', 'submitted_ideas_count', 'deadline_for_idea_submission'];
        const rows = allProblems.map(p => headers.map(h => `"${(p[h] || '').toString().replace(/"/g, '""')}"`).join(','));
        const csv = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sih_2026_problems_${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.toString().replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // ── Analytics & Visitor Tracking ──────────────────
    async function logVisitor() {
        try {
            let sessionId = localStorage.getItem('sih_visitor_session');
            if (!sessionId) {
                sessionId = 'sih_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
                localStorage.setItem('sih_visitor_session', sessionId);
            }
            const res = await api('/api/analytics/visit', {
                method: 'POST',
                body: JSON.stringify({
                    session_id: sessionId,
                    path: window.location.pathname,
                    referrer: document.referrer || null
                })
            });
            if (res && res.unique_visitors) {
                const userCountEl = document.getElementById('user-count-display');
                if (userCountEl) userCountEl.textContent = `👥 ${res.unique_visitors}+ Users`;
            }
        } catch (e) {
            console.warn('Analytics visit log skipped:', e);
        }
    }

    // ── Ratings & Feedback Logic ───────────────────────
    let currentRatingScore = 5;
    let currentRatingCategory = 'Overall Experience';
    let currentRatingTargetType = 'platform';
    let currentRatingTargetId = 'general';

    function setRatingValue(val) {
        currentRatingScore = val;
        const starButtons = document.querySelectorAll('#star-picker .star-btn');
        starButtons.forEach(btn => {
            const starVal = parseInt(btn.dataset.val);
            btn.classList.toggle('active', starVal <= val);
        });
        const numLabel = document.getElementById('rating-score-num');
        if (numLabel) numLabel.textContent = `${val}.0 / 5.0`;
    }

    function setRatingCategory(btn, cat) {
        currentRatingCategory = cat;
        document.querySelectorAll('#rating-category-tags .feedback-tag-btn').forEach(b => b.classList.remove('active'));
        if (btn) btn.classList.add('active');
    }

    async function loadRatingsSummary(targetType = 'platform', targetId = 'general') {
        try {
            const data = await api(`/api/ratings/stats?target_type=${encodeURIComponent(targetType)}&target_id=${encodeURIComponent(targetId)}`);
            if (data) {
                const avgBadge = document.getElementById('rating-modal-avg-badge');
                if (avgBadge) avgBadge.textContent = `⭐ ${data.average_rating} (${data.total_reviews} reviews)`;

                const platformBadge = document.getElementById('platform-rating-display');
                if (platformBadge) platformBadge.textContent = `⭐ ${data.average_rating} (${data.total_reviews || 18})`;

                const streamEl = document.getElementById('rating-reviews-stream');
                if (streamEl) {
                    if (!data.recent_reviews || data.recent_reviews.length === 0) {
                        streamEl.innerHTML = '<p style="font-size:0.8rem; color:var(--text-muted); text-align:center; padding:10px;">Be the first to share your thoughts!</p>';
                    } else {
                        streamEl.innerHTML = data.recent_reviews.map(r => `
                            <div class="review-item">
                                <div class="review-top">
                                    <span class="review-author">${escapeHtml(r.author_name || 'Anonymous Hacker')}</span>
                                    <span class="review-stars">${'★'.repeat(r.rating)}${'☆'.repeat(5 - r.rating)}</span>
                                </div>
                                <div class="review-body">${escapeHtml(r.review_text || 'No comment text.')}</div>
                                <div class="review-meta-bar">
                                    <span>🏷️ ${escapeHtml(r.category || 'Overall')}</span>
                                    ${r.created_at ? `<span>• ${escapeHtml(r.created_at)}</span>` : ''}
                                </div>
                            </div>
                        `).join('');
                    }
                }
            }
        } catch (e) {
            console.warn('Failed to load ratings:', e);
        }
    }

    function openRatingModal(targetType = 'platform', targetId = 'general', title = null) {
        currentRatingTargetType = targetType;
        currentRatingTargetId = targetId;

        const titleEl = document.getElementById('rating-modal-title');
        const subEl = document.getElementById('rating-modal-subtitle');
        if (titleEl) {
            if (title) {
                titleEl.textContent = `⭐ Rate: ${title}`;
            } else if (targetType === 'problem_statement') {
                titleEl.textContent = `⭐ Rate Problem Statement (${targetId})`;
            } else {
                titleEl.textContent = '⭐ Rate Platform & Project Intelligence';
            }
        }
        if (subEl) {
            subEl.textContent = targetType === 'problem_statement' 
                ? `Rate relevance, domain clarity, and AI prompt suitability for ${targetId}.` 
                : 'Help us improve the SIH 2026 Intelligence Platform. Share your rating and feedback on problem accuracy, AI suggestions, or prompt quality.';
        }

        setRatingValue(5);
        loadRatingsSummary(targetType, targetId);

        const modal = document.getElementById('modal-rating');
        if (modal) modal.style.display = 'flex';
    }

    function openProblemRatingModal() {
        if (!currentModalProblem) return;
        openRatingModal('problem_statement', currentModalProblem.problem_statement_id, `${currentModalProblem.problem_statement_id} - ${currentModalProblem.title.substring(0, 40)}...`);
    }

    function closeRatingModal() {
        const modal = document.getElementById('modal-rating');
        if (modal) modal.style.display = 'none';
    }

    async function submitUserRating() {
        const authorInput = document.getElementById('rating-author');
        const commentInput = document.getElementById('rating-comments');

        const payload = {
            rating: currentRatingScore,
            target_type: currentRatingTargetType,
            target_id: currentRatingTargetId,
            author_name: authorInput ? authorInput.value.trim() : '',
            category: currentRatingCategory,
            review_text: commentInput ? commentInput.value.trim() : ''
        };

        try {
            const res = await api('/api/ratings', {
                method: 'POST',
                body: JSON.stringify(payload)
            });

            copyToClipboard('', '⭐ Thank you for rating! Your review has been saved.');
            if (commentInput) commentInput.value = '';
            
            // Reload stats and reviews stream
            await loadRatingsSummary(currentRatingTargetType, currentRatingTargetId);
            setTimeout(() => closeRatingModal(), 1200);
        } catch (e) {
            alert(`Failed to submit rating: ${e.message}`);
        }
    }

    // ── Boot ─────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', init);

    return {
        navigate,
        openModal,
        closeModal,
        openRatingModal,
        openProblemRatingModal,
        closeRatingModal,
        setRatingValue,
        setRatingCategory,
        submitUserRating,
        switchModalTab,
        copyCurrentPSID,
        copyRAGPrompt,
        analyzeFromModal,
        setViewMode,
        resetFilters,
        toggleBookmark,
        toggleBookmarkFilter,
        startAnalysis,
        showDeepMatch,
        togglePivotAdvisorCard,
        backToMatches,
        copyPromptText,
        exportJSON,
        exportCSV
    };
})();


