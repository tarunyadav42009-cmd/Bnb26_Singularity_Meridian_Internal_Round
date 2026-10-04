"use strict";

const API_BASE = "/api";
let latestVerification = null;
let sourceReady = false;

function $(id) { return document.getElementById(id); }

function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function shortHash(hash) {
    if (!hash) return "—";
    if (hash.length <= 24) return hash;
    return `${hash.slice(0, 14)}…${hash.slice(-10)}`;
}

function formatTime(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString();
}

function formatBytes(bytes) {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let value = Number(bytes);
    let index = 0;
    while (value >= 1024 && index < units.length - 1) {
        value /= 1024;
        index += 1;
    }
    return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

async function apiFetch(endpoint, options = {}) {
    const response = await fetch(API_BASE + endpoint, {
        ...options,
        cache: "no-store",
        headers: { Accept: "application/json", ...(options.headers || {}) },
    });
    const text = await response.text();
    let data;
    try { data = JSON.parse(text); }
    catch { throw new Error(`Unreadable API response (${response.status})`); }
    if (!response.ok) throw new Error(data.error || data.message || `HTTP ${response.status}`);
    return data;
}

async function checkHealth() {
    try {
        await apiFetch("/health");
        setConnectionState(true, "API connected");
        $("systemStatus").textContent = "Operational";
        $("systemStatus").className = "system-status operational";
        $("systemStatusText").textContent = "Verification API responding";
        $("footerApiStatus").textContent = "API online";
        return true;
    } catch (error) {
        console.error(error);
        setConnectionState(false, "API unavailable");
        $("systemStatus").textContent = "Unavailable";
        $("systemStatus").className = "system-status failed";
        $("systemStatusText").textContent = "Flask backend is not reachable on port 5000";
        $("footerApiStatus").textContent = "API unavailable";
        return false;
    }
}

function setConnectionState(online, label) {
    $("connectionBadge").classList.toggle("online", online);
    $("connectionBadge").classList.toggle("offline", !online);
    $("connectionText").textContent = label;
}

function setVerifyEnabled(enabled, label = "BUILD & VERIFY SOURCE") {
    $("verifyBtn").disabled = !enabled;
    $("verifyBtn").textContent = label;
}

function renderSourceInfo(data) {
    sourceReady = true;
    $("sourceState").textContent = "SOURCE READY";
    $("sourceState").className = "source-state ready";
    $("selectedSource").textContent = data.filename || "Source loaded";
    $("sourceInfo").classList.remove("hidden");
    $("sourceName").textContent = data.filename || "—";
    $("sourceType").textContent = data.type || "SOURCE";
    $("sourceFiles").textContent = String(data.file_count ?? "—");
    $("sourceHash").textContent = data.source_hash || "—";
    setVerifyEnabled(true);
    $("systemStatus").textContent = "Source ready";
    $("systemStatus").className = "system-status operational";
    $("systemStatusText").textContent = "Source snapshot loaded. Build & Verify is ready.";
}

function clearSourceUI() {
    sourceReady = false;
    $("sourceState").textContent = "NO SOURCE";
    $("sourceState").className = "source-state";
    $("selectedSource").textContent = "No source package selected.";
    $("sourceInfo").classList.add("hidden");
    $("sourceName").textContent = "—";
    $("sourceType").textContent = "—";
    $("sourceFiles").textContent = "—";
    $("sourceHash").textContent = "—";
    setVerifyEnabled(false, "BUILD & VERIFY SOURCE");
    renderPending();
}

async function loadSourceStatus() {
    try {
        const data = await apiFetch("/source/status");
        if (data.ready) {
            renderSourceInfo(data);
        } else {
            clearSourceUI();
        }
    } catch (error) {
        console.error(error);
        clearSourceUI();
    }
}

function setupSourceInput() {
    $("sourceZip").addEventListener("change", () => {
        const file = $("sourceZip").files?.[0];
        $("selectedSource").textContent = file
            ? `${file.name} · ${formatBytes(file.size)}`
            : "No source package selected.";
        if (file) $("sourceState").textContent = "READY TO LOAD";
    });
    $("uploadSourceBtn").addEventListener("click", uploadSource);
    $("githubSourceBtn").addEventListener("click", loadGithubSource);
}

async function uploadSource() {
    const file = $("sourceZip").files?.[0];
    if (!file) { alert("Choose a source ZIP first."); return; }
    if (!file.name.toLowerCase().endsWith(".zip")) { alert("Only ZIP source packages are supported."); return; }
    const formData = new FormData();
    formData.append("source", file);
    $("uploadSourceBtn").disabled = true;
    $("uploadSourceBtn").textContent = "LOADING SOURCE...";
    try {
        const response = await fetch(API_BASE + "/source/upload", { method: "POST", body: formData, cache: "no-store" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || data.message || "Source upload failed.");
        renderSourceInfo(data);
    } catch (error) {
        alert(error.message);
    } finally {
        $("uploadSourceBtn").disabled = false;
        $("uploadSourceBtn").textContent = "LOAD SOURCE";
    }
}

async function loadGithubSource() {
    const url = $("githubUrl").value.trim();
    if (!url) { alert("Enter a public GitHub repository URL."); return; }
    $("githubSourceBtn").disabled = true;
    $("githubSourceBtn").textContent = "LOADING REPOSITORY...";
    try {
        const data = await apiFetch("/source/github", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });
        renderSourceInfo(data);
    } catch (error) {
        alert(error.message);
    } finally {
        $("githubSourceBtn").disabled = false;
        $("githubSourceBtn").textContent = "LOAD REPOSITORY";
    }
}

async function runVerification() {
    if (!sourceReady) {
        alert("Submit a source package or GitHub repository before verification.");
        return;
    }
    setButtonsBusy(true, "BUILDING & VERIFYING...");
    $("demoNotice").classList.add("hidden");
    try {
        const data = await apiFetch("/api/verify".replace("/api/", "/"), { method: "POST" });
        latestVerification = data;
        renderVerification(data);
        $("systemStatus").textContent = data.status === "ACCEPT" ? "Operational · Trusted" : data.status === "REJECT" ? "Operational · Build Rejected" : "Operational";
        $("systemStatus").className = data.status === "ACCEPT" ? "system-status operational" : data.status === "REJECT" ? "system-status failed" : "system-status operational";
        $("systemStatusText").textContent = data.message || "Verification completed.";
        $("footerApiStatus").textContent = "API online · source verified";
    } catch (error) {
        renderError(error);
    } finally {
        setButtonsBusy(false, "BUILD & VERIFY SOURCE");
    }
}

async function runTwoFailDemo() {
    if (!sourceReady) {
        alert("Submit source code before running the failure demo.");
        return;
    }
    setButtonsBusy(true, "SIMULATING FAILURE...");
    try {
        const data = await apiFetch("/demo/reject", { method: "POST" });
        latestVerification = data;
        renderVerification(data);
        $("demoNotice").classList.remove("hidden");
        $("systemStatus").textContent = "Operational · Attack Simulation";
        $("systemStatus").className = "system-status failed";
        $("systemStatusText").textContent = "Builder B and Builder C are unavailable in demo mode";
        $("footerApiStatus").textContent = "API online · REJECT demo";
        await loadAuditStatus();
        await loadAuditEntries();
    } catch (error) {
        renderError(error);
    } finally {
        setButtonsBusy(false, "BUILD & VERIFY SOURCE");
    }
}

function renderPending() {
    $("verifiedCount").textContent = "—";
    $("verifiedHint").textContent = "Source submission required";
    $("quorumStrength").textContent = "—";
    $("quorumHint").textContent = "Required consensus: 2";
    $("hashCount").textContent = "—";
    $("hashHint").textContent = "SHA-256 integrity checks";
    $("lastRun").textContent = "NOT RUN";
    $("decisionBanner").classList.remove("accept", "reject");
    $("decisionBanner").classList.add("pending");
    $("decisionStatus").textContent = "SOURCE REQUIRED";
    $("decisionMessage").textContent = "Submit source code before running the builder network.";
    $("decisionQuorum").textContent = "—";
    $("decisionRequired").textContent = "2";
    $("winningGroup").textContent = "—";
    $("decisionOutliers").textContent = "None";
    $("winningHash").textContent = "—";
    $("builderGrid").innerHTML = `<div class="empty-state">Submit source code to start a real verification run.</div>`;
    $("builderNetworkGrid").innerHTML = `<div class="empty-state">No builder run yet.</div>`;
}

function renderVerification(data) {
    const builders = Array.isArray(data.builders) ? data.builders : [];
    const total = Number(data.total_builders ?? builders.length ?? 3);
    const verified = Number(data.verified_builders ?? 0);
    const quorum = Number(data.quorum ?? 0);
    const required = Number(data.required_quorum ?? data.required ?? 2);
    const status = String(data.status || "PENDING").toUpperCase();
    const winningHash = data.winning_hash || data.decision?.winning_hash || null;

    $("verifiedCount").textContent = `${verified}/${total}`;
    $("verifiedHint").textContent = verified >= required ? "Consensus threshold achieved" : "Below consensus threshold";
    $("quorumStrength").textContent = `${quorum}/${required}`;
    $("quorumHint").textContent = quorum >= required ? "Quorum reached" : `Need ${required - quorum} more builder(s)`;

    const matching = builders.filter(item => item.verified === true && item.hash_valid === true && (!winningHash || item.artifact_hash === winningHash)).length;
    $("hashCount").textContent = `${matching}/${total}`;
    $("hashHint").textContent = matching === total && total > 0 ? "All artifact hashes match" : "Hash agreement incomplete";

    $("lastRun").textContent = `LAST RUN · ${formatTime(data.audit_event?.timestamp || new Date().toISOString())}`;
    renderBuilders(builders, data.outliers || []);
    renderDecision(data, status, required);
    renderAuditSummary(data.audit || {});
    loadAuditEntries();
}

function renderBuilders(builders, outliers) {
    if (!builders.length) {
        const empty = `<div class="empty-state">No builder verification data available.</div>`;
        $("builderGrid").innerHTML = empty;
        $("builderNetworkGrid").innerHTML = empty;
        return;
    }
    const html = builders.map(builder => builderCard(builder, outliers)).join("");
    $("builderGrid").innerHTML = html;
    $("builderNetworkGrid").innerHTML = html;
}

function builderCard(builder, outliers) {
    const id = String(builder.builder_id || "unknown");
    const verified = builder.verified === true;
    const outlier = outliers.includes(id);
    const cardClass = outlier ? "builder-card outlier" : verified ? "builder-card verified" : "builder-card failed";
    const badge = outlier ? `<span class="state-badge warn">OUTLIER</span>` : verified ? `<span class="state-badge pass">VERIFIED</span>` : `<span class="state-badge fail">FAILED</span>`;
    const artifactPass = builder.artifact_file_valid === true || Boolean(builder.artifact && builder.artifact_hash);
    const actualHash = verified ? (builder.actual_hash || builder.artifact_hash || "—") : "Not calculated — builder unavailable";

    return `
        <article class="${cardClass}">
            <div class="builder-top">
                <div class="builder-name">
                    <div class="builder-avatar">${escapeHtml(id.replace("builder-", "").toUpperCase())}</div>
                    <div>
                        <div class="builder-title">${escapeHtml(id.toUpperCase())}</div>
                        <div class="builder-state">${escapeHtml(builder.artifact || "No artifact")}</div>
                    </div>
                </div>
                ${badge}
            </div>
            <div class="check-list">
                ${checkRow("Artifact file", artifactPass)}
                ${checkRow("SHA-256 hash", builder.hash_valid === true)}
                ${checkRow("Trusted signature", builder.signature_valid === true)}
                ${checkRow("Source attestation", builder.attestation_valid === true)}
            </div>
            <div class="hash-box">
                <span class="hash-label">ARTIFACT SHA-256</span>
                <code class="hash-value">${escapeHtml(actualHash)}</code>
            </div>
            <div class="reason">${escapeHtml(builder.error || builder.reason || (verified ? "All cryptographic checks passed." : "Verification failed."))}</div>
        </article>
    `;
}

function checkRow(label, pass) {
    return `<div class="check-row"><span>${escapeHtml(label)}</span><span class="check-value ${pass ? "pass" : "fail"}">${pass ? "PASS" : "FAIL"}</span></div>`;
}

function renderDecision(data, status, required) {
    const decision = data.decision || {};
    const winningHash = data.winning_hash || decision.winning_hash || null;
    const winningGroup = Array.isArray(data.winning_group) ? data.winning_group : (decision.winning_group || []);
    const outliers = Array.isArray(data.outliers) ? data.outliers : (decision.outliers || []);
    const banner = $("decisionBanner");
    banner.classList.remove("accept", "reject", "pending");
    banner.classList.add(status === "ACCEPT" ? "accept" : status === "REJECT" ? "reject" : "pending");
    $("decisionStatus").textContent = status;
    $("decisionMessage").textContent = data.message || decision.message || "Verification pending.";
    $("decisionQuorum").textContent = String(data.quorum ?? decision.quorum ?? 0);
    $("decisionRequired").textContent = String(required);
    $("winningGroup").textContent = winningGroup.length ? winningGroup.map(name => name.toUpperCase()).join(" · ") : "None";
    $("decisionOutliers").textContent = outliers.length ? outliers.map(name => name.toUpperCase()).join(" · ") : "None";
    $("winningHash").textContent = winningHash || "None";
}

async function loadAuditStatus() {
    try {
        const data = await apiFetch("/audit/status");
        renderAuditSummary(data);
    } catch {
        renderAuditSummary({ valid: false, message: "Audit status unavailable." });
    }
}

function renderAuditSummary(audit) {
    const valid = audit.valid === true;
    $("auditState").textContent = valid ? "VALID" : "ALERT";
    $("auditHint").textContent = valid ? "Hash chain intact" : (audit.message || "Audit chain requires attention");
    const panel = $("auditStatePanel");
    panel.classList.remove("valid", "tampered");
    panel.classList.add(valid ? "valid" : "tampered");
    panel.textContent = valid ? `✓ Audit chain integrity verified · ${audit.message || "Audit log is valid."}` : `⚠ ${audit.message || "Audit status unavailable."}`;
}

async function loadAuditEntries() {
    try {
        const data = await apiFetch("/audit/entries?limit=10");
        const entries = data.entries || [];
        $("auditEntries").innerHTML = entries.length ? entries.map(entry => `
            <article class="audit-entry">
                <div class="audit-entry-top">
                    <div class="audit-event">${escapeHtml(entry.event || "EVENT")}</div>
                    <div class="audit-time">${escapeHtml(formatTime(entry.timestamp))}</div>
                </div>
                <div class="audit-entry-bottom">
                    <div class="audit-chain">CHAINED</div>
                    <div class="audit-hash">${escapeHtml(shortHash(entry.entry_hash || "—"))}</div>
                </div>
            </article>
        `).join("") : `<div class="empty-state">Audit events will appear after a verification run.</div>`;
    } catch {
        $("auditEntries").innerHTML = `<div class="empty-state">Audit events unavailable.</div>`;
    }
}

function renderError(error) {
    setConnectionState(false, "API error");
    $("systemStatus").textContent = "Unavailable";
    $("systemStatus").className = "system-status failed";
    $("systemStatusText").textContent = error.message || "Verification failed.";
    $("footerApiStatus").textContent = "API error";
    $("decisionBanner").classList.remove("accept", "pending");
    $("decisionBanner").classList.add("reject");
    $("decisionStatus").textContent = "ERROR";
    $("decisionMessage").textContent = error.message || "Verification failed.";
}

function setButtonsBusy(busy, label) {
    [$("verifyBtn"), $("demoBtn"), $("builderRefreshBtn")].forEach(button => {
        if (button) button.disabled = busy || (!sourceReady && (button === $("verifyBtn") || button === $("demoBtn")));
    });
    $("verifyBtn").textContent = busy ? label : "BUILD & VERIFY SOURCE";
}

function setupTabs() {
    document.querySelectorAll(".nav-item").forEach(button => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
            button.classList.add("active");
            document.querySelectorAll(".tab-content").forEach(tab => tab.classList.remove("active"));
            const target = $("tab-" + button.dataset.tab);
            if (target) target.classList.add("active");
        });
    });
}

function setupEvents() {
    $("verifyBtn").addEventListener("click", runVerification);
    $("builderRefreshBtn").addEventListener("click", runVerification);
    $("auditRefreshBtn").addEventListener("click", async () => { await loadAuditStatus(); await loadAuditEntries(); });
}

async function initialize() {
    setupTabs();
    setupSourceInput();
    setupEvents();
    renderPending();
    setVerifyEnabled(false);
    const online = await checkHealth();
    if (!online) return;
    await loadSourceStatus();
    await loadAuditStatus();
    await loadAuditEntries();
}

document.addEventListener("DOMContentLoaded", initialize);
