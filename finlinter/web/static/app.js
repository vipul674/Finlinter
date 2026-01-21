/**
 * Financial Code Validator - Frontend JavaScript
 * Handles code scanning, results display, and UI interactions
 */

(function () {
    'use strict';

    // DOM Elements
    const codeInput = document.getElementById('code-input');
    const scanBtn = document.getElementById('scan-btn');
    const lineNumbers = document.getElementById('line-numbers');
    const resultsSection = document.getElementById('results-section');
    const scanMeta = document.getElementById('scan-meta');
    const findingsCount = document.getElementById('findings-count');
    const perExecutionCost = document.getElementById('per-execution-cost');
    const monthlyCost = document.getElementById('monthly-cost');
    const severityBreakdown = document.getElementById('severity-breakdown');
    const findingsList = document.getElementById('findings-list');
    const noIssues = document.getElementById('no-issues');
    const summaryCard = document.getElementById('summary-card');
    const disclaimer = document.getElementById('disclaimer');
    const languageSelect = document.getElementById('language-select');

    // Initialize
    function init() {
        // Set up event listeners
        codeInput.addEventListener('input', updateLineNumbers);
        codeInput.addEventListener('scroll', syncScroll);
        scanBtn.addEventListener('click', handleScan);
        codeInput.addEventListener('keydown', handleTab);

        // Clear button
        const clearBtn = document.getElementById('clear-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', handleClear);
        }

        // Initial line numbers
        updateLineNumbers();
    }

    // Handle clear button click
    function handleClear() {
        codeInput.value = '';
        resultsSection.style.display = 'none';
        updateLineNumbers();
        codeInput.focus();
    }

    // Update line numbers based on textarea content
    function updateLineNumbers() {
        const lines = codeInput.value.split('\n');
        const numbers = lines.map((_, i) => i + 1).join('\n');
        lineNumbers.textContent = numbers || '1';
    }

    // Sync scroll between textarea and line numbers
    function syncScroll() {
        lineNumbers.style.transform = `translateY(-${codeInput.scrollTop}px)`;
    }

    // Handle Tab key for indentation
    function handleTab(e) {
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = codeInput.selectionStart;
            const end = codeInput.selectionEnd;
            const value = codeInput.value;

            codeInput.value = value.substring(0, start) + '    ' + value.substring(end);
            codeInput.selectionStart = codeInput.selectionEnd = start + 4;
            updateLineNumbers();
        }
    }

    // Handle scan button click
    async function handleScan() {
        const code = codeInput.value.trim();
        const language = languageSelect ? languageSelect.value : 'auto';

        if (!code) {
            showError('Please paste some code to analyze.');
            return;
        }

        // Show loading state
        scanBtn.disabled = true;
        scanBtn.classList.add('loading');
        scanBtn.innerHTML = '<span class="btn-icon">⟳</span> Analyzing...';

        try {
            const response = await fetch('/scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    code: code,
                    language: language,
                }),
            });

            const data = await response.json();

            if (!data.success) {
                showError(data.error || 'Analysis failed');
                return;
            }

            displayResults(data.result, data.summary);

        } catch (error) {
            showError('Network error: Could not connect to the server.');
            console.error('Scan error:', error);
        } finally {
            // Reset button
            scanBtn.disabled = false;
            scanBtn.classList.remove('loading');
            scanBtn.innerHTML = '<span class="btn-icon">⚡</span> Analyze';
        }
    }

    // Display scan results
    function displayResults(result, summary) {
        // Show results section
        resultsSection.style.display = 'block';

        // Update scan meta - show language if auto-detected
        const languageDisplay = result.language ? result.language.charAt(0).toUpperCase() + result.language.slice(1) : 'Unknown';
        scanMeta.textContent = `${languageDisplay} • ${result.scan_time_ms.toFixed(1)}ms`;

        // Update summary
        findingsCount.textContent = summary.findings_count;
        perExecutionCost.textContent = formatCost(summary.total_per_execution);
        monthlyCost.textContent = formatCost(summary.total_monthly);

        // Show disclaimer
        if (disclaimer && summary.disclaimer) {
            disclaimer.textContent = `⚠️ ${summary.disclaimer}`;
            disclaimer.style.display = 'block';
        }

        // Count severities from actual findings
        const severityCounts = { high: 0, medium: 0, low: 0 };
        for (const finding of result.findings) {
            const sev = finding.severity.toLowerCase();
            if (severityCounts.hasOwnProperty(sev)) {
                severityCounts[sev]++;
            }
        }

        // Update severity breakdown with correct counts
        updateSeverityBreakdown(severityCounts);

        // Display findings or no-issues message
        if (result.findings.length === 0) {
            summaryCard.style.display = 'none';
            findingsList.style.display = 'none';
            noIssues.style.display = 'block';
        } else {
            summaryCard.style.display = 'block';
            findingsList.style.display = 'flex';
            noIssues.style.display = 'none';
            renderFindings(result.findings);
        }

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Update severity breakdown display
    function updateSeverityBreakdown(counts) {
        severityBreakdown.innerHTML = '';

        const severities = ['high', 'medium', 'low'];
        for (const severity of severities) {
            if (counts[severity] > 0) {
                const badge = document.createElement('div');
                badge.className = `severity-badge ${severity}`;
                badge.innerHTML = `
                    <span class="severity-dot"></span>
                    ${capitalize(severity)}: ${counts[severity]}
                `;
                severityBreakdown.appendChild(badge);
            }
        }
    }

    // Render findings list - MVP output format
    function renderFindings(findings) {
        findingsList.innerHTML = '';

        for (const finding of findings) {
            const card = document.createElement('div');
            card.className = `finding-card severity-${finding.severity}`;

            // Build cost display per MVP spec
            let costDisplay = '';
            if (finding.estimated_cost) {
                const perExec = formatCost(finding.estimated_cost.per_execution_cost);
                const monthly = formatCost(finding.estimated_cost.monthly_cost);
                costDisplay = `
                    <div class="finding-cost-section">
                        <div class="cost-label">Estimated Cost:</div>
                        <div class="cost-value">${perExec} per execution</div>
                        <div class="cost-value">≈ ${monthly} per month (daily runs)</div>
                    </div>
                `;
            }

            // Build "Why this matters" explanation
            const whyMatters = getWhyItMatters(finding.rule_id, finding.description);

            card.innerHTML = `
                <div class="finding-header">
                    <div class="warning-icon">⚠️</div>
                    <div class="warning-title">Financial Bug Detected</div>
                </div>
                <div class="finding-body">
                    <div class="finding-detail">
                        <span class="detail-label">Pattern:</span>
                        <span class="detail-value">${escapeHtml(finding.rule_name)}</span>
                    </div>
                    <div class="finding-detail">
                        <span class="detail-label">Line:</span>
                        <span class="detail-value">${finding.line_number}</span>
                    </div>
                    <div class="finding-detail">
                        <span class="detail-label">Severity:</span>
                        <span class="detail-value severity-text ${finding.severity}">${capitalize(finding.severity)}</span>
                    </div>
                    
                    ${costDisplay}
                    
                    <div class="finding-why">
                        <div class="why-label">Why this matters:</div>
                        <div class="why-content">${escapeHtml(whyMatters)}</div>
                    </div>
                    
                    <div class="finding-fix">
                        <div class="fix-label">Recommended Fix:</div>
                        <div class="fix-content">${escapeHtml(finding.suggestion)}</div>
                    </div>
                    
                    <div class="finding-code">
                        <code>${escapeHtml(finding.line_content)}</code>
                    </div>
                </div>
            `;

            findingsList.appendChild(card);
        }
    }

    // Get "Why it matters" explanation based on rule
    function getWhyItMatters(ruleId, description) {
        const explanations = {
            'PY001': 'Each loop iteration triggers a paid database operation, causing N+1 query problems.',
            'PY002': 'Each loop iteration triggers a paid API request, multiplying costs by iteration count.',
            'PY003': 'Repeated serialization inside loops consumes CPU resources unnecessarily.',
            'PY004': 'Queries without LIMIT may return excessive data, increasing response time and costs.',
        };
        return explanations[ruleId] || description;
    }

    // Show error message
    function showError(message) {
        resultsSection.style.display = 'block';
        summaryCard.style.display = 'none';
        findingsList.style.display = 'none';
        noIssues.style.display = 'none';

        findingsList.style.display = 'block';
        findingsList.innerHTML = `
            <div class="error-message">
                <span>❌</span>
                <span>${escapeHtml(message)}</span>
            </div>
        `;

        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Format cost for display in ₹
    function formatCost(amount) {
        if (amount >= 1000) {
            return `₹${amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        } else if (amount >= 1) {
            return `₹${amount.toFixed(2)}`;
        } else if (amount >= 0.01) {
            return `₹${amount.toFixed(2)}`;
        } else {
            return `₹${amount.toFixed(4)}`;
        }
    }

    // Capitalize first letter
    function capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
