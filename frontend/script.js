"use strict";


/*
 * ============================================================
 * QUORUM FRONTEND
 * ============================================================
 *
 * This API selection works in both cases:
 *
 * 1. Flask:
 *      http://127.0.0.1:5000/
 *
 * 2. Direct/Live Server:
 *      http://127.0.0.1:5500/
 *      file://...
 *
 * In the second case it explicitly talks to Flask:5000.
 */

const API_BASE =
    (
        window.location.protocol === "http:" &&
        (
            window.location.port === "5000" ||
            window.location.hostname === "127.0.0.1" ||
            window.location.hostname === "localhost"
        )
    )
        ? "/api"
        : "http://127.0.0.1:5000/api";


let latestVerification = null;

let latestAudit = null;

let sourceReady = false;


/* ============================================================
   DOM
   ============================================================ */

function $(id) {

    return document.getElementById(id);
}


function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function shortHash(hash) {

    if (!hash) {
        return "—";
    }

    if (hash.length <= 24) {
        return hash;
    }

    return (
        hash.slice(0, 14)
        + "…"
        + hash.slice(-10)
    );
}


function formatTime(value) {

    if (!value) {
        return "—";
    }

    const date =
        new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return String(value);
    }

    return date.toLocaleString();
}


function formatBytes(bytes) {

    if (!bytes) {
        return "0 B";
    }

    const units = [
        "B",
        "KB",
        "MB",
        "GB"
    ];

    let value =
        Number(bytes);

    let index = 0;

    while (
        value >= 1024 &&
        index < units.length - 1
    ) {

        value =
            value / 1024;

        index++;
    }

    return (
        value.toFixed(
            index === 0
                ? 0
                : 1
        )
        + " "
        + units[index]
    );
}


/* ============================================================
   API HELPER
   ============================================================ */

async function apiFetch(
    endpoint,
    options = {}
) {

    const response =
        await fetch(
            API_BASE + endpoint,
            {
                ...options,

                cache: "no-store",

                headers: {
                    "Accept":
                        "application/json",

                    ...(options.headers || {})
                }
            }
        );


    const text =
        await response.text();


    let data;


    try {

        data =
            JSON.parse(text);

    } catch {

        throw new Error(
            `Unreadable API response (${response.status})`
        );
    }


    if (!response.ok) {

        throw new Error(
            data.error
            || data.message
            || `HTTP ${response.status}`
        );
    }


    return data;
}


/* ============================================================
   HEALTH
   ============================================================ */

async function checkHealth() {

    try {

        await apiFetch(
            "/health"
        );


        setConnectionState(
            true,
            "API connected"
        );


        $("systemStatus").textContent =
            "Operational";


        $("systemStatus").className =
            "system-status operational";


        $("systemStatusText").textContent =
            "Verification API responding";


        $("footerApiStatus").textContent =
            "API online";


        return true;


    } catch (error) {

        console.error(
            "Health check failed:",
            error
        );


        setConnectionState(
            false,
            "API unavailable"
        );


        $("systemStatus").textContent =
            "Unavailable";


        $("systemStatus").className =
            "system-status failed";


        $("systemStatusText").textContent =
            "Flask backend not reachable on port 5000";


        $("footerApiStatus").textContent =
            "API unavailable";


        return false;
    }
}


function setConnectionState(
    online,
    label
) {

    const badge =
        $("connectionBadge");

    const text =
        $("connectionText");


    if (
        !badge ||
        !text
    ) {

        return;
    }


    badge.classList.toggle(
        "online",
        online
    );


    badge.classList.toggle(
        "offline",
        !online
    );


    text.textContent =
        label;
}


/* ============================================================
   SOURCE INPUT
   ============================================================ */

function setupSourceInput() {

    const zipInput =
        $("sourceZip");

    const uploadButton =
        $("uploadSourceBtn");

    const githubButton =
        $("githubSourceBtn");


    if (zipInput) {

        zipInput.addEventListener(
            "change",
            () => {

                const file =
                    zipInput.files?.[0];


                if (file) {

                    $("selectedSource").textContent =
                        `${file.name} · ${formatBytes(file.size)}`;


                    $("sourceState").textContent =
                        "READY TO LOAD";

                } else {

                    $("selectedSource").textContent =
                        "No source package selected.";


                    $("sourceState").textContent =
                        "NO SOURCE";
                }
            }
        );
    }


    if (uploadButton) {

        uploadButton.addEventListener(
            "click",
            uploadSource
        );
    }


    if (githubButton) {

        githubButton.addEventListener(
            "click",
            loadGithubSource
        );
    }
}


async function uploadSource() {

    const input =
        $("sourceZip");

    const button =
        $("uploadSourceBtn");


    if (!input) {
        return;
    }


    const file =
        input.files?.[0];


    if (!file) {

        alert(
            "Please choose a source ZIP first."
        );

        return;
    }


    if (
        !file.name
            .toLowerCase()
            .endsWith(".zip")
    ) {

        alert(
            "Only ZIP source packages are supported."
        );

        return;
    }


    const formData =
        new FormData();


    formData.append(
        "source",
        file
    );


    if (button) {

        button.disabled =
            true;

        button.textContent =
            "LOADING...";
    }


    try {

        const response =
            await fetch(
                API_BASE + "/source/upload",
                {
                    method: "POST",
                    body: formData,
                    cache: "no-store"
                }
            );


        const text =
            await response.text();


        let data;


        try {

            data =
                JSON.parse(text);

        } catch {

            throw new Error(
                `Invalid source API response (${response.status})`
            );
        }


        if (!response.ok) {

            throw new Error(
                data.error
                || data.message
                || "Source upload failed."
            );
        }


        sourceReady =
            true;


        renderSourceInfo(
            data
        );


        $("systemStatus").textContent =
            "Source loaded";


        $("systemStatus").className =
            "system-status operational";


        $("systemStatusText").textContent =
            "Source package loaded into QUORUM workspace";


    } catch (error) {

        console.error(
            "Source upload error:",
            error
        );


        sourceReady =
            false;


        alert(
            error.message
            || "Unable to load source package."
        );


    } finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                "LOAD SOURCE";
        }
    }
}


async function loadGithubSource() {

    const input =
        $("githubUrl");

    const button =
        $("githubSourceBtn");


    if (!input) {
        return;
    }


    const url =
        input.value.trim();


    if (!url) {

        alert(
            "Enter a public GitHub repository URL."
        );

        return;
    }


    if (button) {

        button.disabled =
            true;

        button.textContent =
            "LOADING...";
    }


    try {

        const data =
            await apiFetch(
                "/source/github",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            url: url
                        })
                }
            );


        sourceReady =
            true;


        renderSourceInfo(
            data
        );


        $("systemStatus").textContent =
            "Repository loaded";


        $("systemStatus").className =
            "system-status operational";


        $("systemStatusText").textContent =
            "GitHub source snapshot loaded into QUORUM workspace";


    } catch (error) {

        console.error(
            "GitHub load error:",
            error
        );


        alert(
            error.message
            || "Unable to load GitHub repository."
        );


    } finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                "LOAD REPOSITORY";
        }
    }
}


function renderSourceInfo(
    data
) {

    $("sourceState").textContent =
        "SOURCE READY";


    $("sourceState").className =
        "source-state ready";


    $("selectedSource").textContent =
        data.filename
        || "Source loaded";


    $("sourceInfo").classList.remove(
        "hidden"
    );


    $("sourceName").textContent =
        data.filename
        || "—";


    $("sourceType").textContent =
        data.type
        || "SOURCE PACKAGE";


    $("sourceFiles").textContent =
        String(
            data.file_count
            ?? "—"
        );


    $("sourceHash").textContent =
        data.source_hash
        || "—";
}


/* ============================================================
   NORMAL VERIFICATION
   ============================================================ */

async function runVerification() {

    setButtonsBusy(
        true,
        "Verifying..."
    );


    $("demoNotice").classList.add(
        "hidden"
    );


    try {

        const data =
            await apiFetch(
                "/verify",
                {
                    method: "POST"
                }
            );


        latestVerification =
            data;


        renderVerification(
            data
        );


        setConnectionState(
            true,
            "API connected"
        );


        $("systemStatus").textContent =
            "Operational";


        $("systemStatus").className =
            "system-status operational";


        $("systemStatusText").textContent =
            sourceReady
                ? "Source loaded · verification completed"
                : "Verification API responding";


        $("footerApiStatus").textContent =
            "API online · verified";


    } catch (error) {

        console.error(
            "Verification error:",
            error
        );


        renderError(
            error
        );


    } finally {

        setButtonsBusy(
            false,
            "↻ Run verification"
        );
    }
}


/* ============================================================
   REJECT DEMO
   ============================================================ */

async function runTwoFailDemo() {

    setButtonsBusy(
        true,
        "Simulating..."
    );


    try {

        const data =
            await apiFetch(
                "/demo/reject",
                {
                    method: "POST"
                }
            );


        latestVerification =
            data;


        renderVerification(
            data
        );


        $("demoNotice").classList.remove(
            "hidden"
        );


        $("systemStatus").textContent =
            "Operational · Attack Simulation";


        $("systemStatus").className =
            "system-status operational";


        $("systemStatusText").textContent =
            "Builder B and Builder C are unavailable in demo mode";


        $("footerApiStatus").textContent =
            "API online · REJECT demo";


        await loadAuditStatus();

        await loadAuditEntries();


    } catch (error) {

        console.error(
            "REJECT DEMO ERROR:",
            error
        );


        renderError(
            error
        );


    } finally {

        setButtonsBusy(
            false,
            "↻ Run verification"
        );
    }
}


/* ============================================================
   VERIFICATION RENDERING
   ============================================================ */

function renderVerification(
    data
) {

    const builders =
        Array.isArray(data.builders)
            ? data.builders
            : [];


    const total =
        Number(
            data.total_builders
            ?? builders.length
            ?? 3
        );


    const verified =
        Number(
            data.verified_builders
            ?? builders.filter(
                b => b.verified === true
            ).length
        );


    const quorum =
        Number(
            data.quorum
            ?? 0
        );


    const required =
        Number(
            data.required_quorum
            ?? data.required
            ?? 2
        );


    const status =
        String(
            data.status
            || "PENDING"
        ).toUpperCase();


    $("verifiedCount").textContent =
        `${verified}/${total}`;


    $("verifiedHint").textContent =
        verified >= required
            ? "Consensus threshold achieved"
            : "Below consensus threshold";


    $("quorumStrength").textContent =
        `${quorum}/${required}`;


    $("quorumHint").textContent =
        quorum >= required
            ? "Quorum reached"
            : `Need ${required - quorum} more builder(s)`;


    const winningHash =
        data.winning_hash
        || data.decision?.winning_hash
        || null;


    const matchingHashCount =
        builders.filter(
            builder =>
                builder.verified === true
                && builder.hash_valid === true
                && (
                    !winningHash
                    || builder.artifact_hash === winningHash
                )
        ).length;


    $("hashCount").textContent =
        `${matchingHashCount}/${total}`;


    $("hashHint").textContent =
        matchingHashCount === total
            ? "All artifact hashes match"
            : "Hash agreement incomplete";


    const timestamp =
        data.audit_event?.timestamp
        || new Date().toISOString();


    $("lastRun").textContent =
        `LAST RUN · ${formatTime(timestamp)}`;


    renderBuilders(
        builders,
        data.outliers || []
    );


    renderDecision(
        data,
        status,
        required
    );


    renderAuditSummary(
        data.audit || {}
    );


    loadAuditEntries();
}


/* ============================================================
   BUILDERS
   ============================================================ */

function renderBuilders(
    builders,
    outliers
) {

    if (!builders.length) {

        const html =
            `<div class="empty-state">
                No builder verification data available.
             </div>`;


        $("builderGrid").innerHTML =
            html;


        $("builderNetworkGrid").innerHTML =
            html;


        return;
    }


    const html =
        builders
            .map(
                builder =>
                    builderCard(
                        builder,
                        outliers
                    )
            )
            .join("");


    $("builderGrid").innerHTML =
        html;


    $("builderNetworkGrid").innerHTML =
        html;
}


function builderCard(
    builder,
    outliers
) {

    const builderId =
        String(
            builder.builder_id
            || "unknown"
        );


    const number =
        builderId
            .replace(
                "builder-",
                ""
            )
            .slice(-1)
            .toUpperCase();


    const verified =
        builder.verified === true;


    const outlier =
        outliers.includes(
            builderId
        );


    const cardClass =
        outlier
            ? "builder-card outlier"
            : verified
                ? "builder-card verified"
                : "builder-card failed";


    let badge;


    if (outlier) {

        badge =
            `<span class="state-badge warn">
                OUTLIER
             </span>`;

    } else if (verified) {

        badge =
            `<span class="state-badge pass">
                VERIFIED
             </span>`;

    } else {

        badge =
            `<span class="state-badge fail">
                FAILED
             </span>`;
    }


    const artifactPass =
        builder.artifact_file_valid === true
        || (
            Boolean(builder.artifact)
            && Boolean(builder.artifact_hash)
        );


    const hashPass =
        builder.hash_valid === true;


    const signaturePass =
        builder.signature_valid === true;


    const attestationPass =
        builder.attestation_valid === true
        || (
            verified
            && hashPass
            && signaturePass
        );


    let actualHash;


    if (
        builder.actual_hash
        && verified
    ) {

        actualHash =
            builder.actual_hash;

    } else if (
        builder.artifact_hash
        && verified
    ) {

        actualHash =
            builder.artifact_hash;

    } else {

        actualHash =
            "Not calculated — builder unavailable";
    }


    return `

        <article class="${cardClass}">

            <div class="builder-top">

                <div class="builder-name">

                    <div class="builder-avatar">
                        B${escapeHtml(number)}
                    </div>

                    <div>

                        <div class="builder-title">
                            ${escapeHtml(
                                builderId.toUpperCase()
                            )}
                        </div>

                        <div class="builder-state">
                            ${escapeHtml(
                                builder.artifact
                                || "No artifact"
                            )}
                        </div>

                    </div>

                </div>

                ${badge}

            </div>


            <div class="check-list">

                ${checkRow(
                    "Artifact file",
                    artifactPass
                )}

                ${checkRow(
                    "SHA-256 hash",
                    hashPass
                )}

                ${checkRow(
                    "Trusted signature",
                    signaturePass
                )}

                ${checkRow(
                    "Attestation",
                    attestationPass
                )}

            </div>


            <div class="hash-box">

                <span class="hash-label">
                    ACTUAL SHA-256
                </span>

                <code class="hash-value">
                    ${escapeHtml(
                        actualHash
                    )}
                </code>

            </div>


            <div class="reason">

                ${escapeHtml(
                    builder.error
                    || builder.reason
                    || (
                        verified
                            ? "All cryptographic checks passed."
                            : "Verification failed."
                    )
                )}

            </div>

        </article>
    `;
}


function checkRow(
    label,
    pass
) {

    return `

        <div class="check-row">

            <span>
                ${escapeHtml(label)}
            </span>

            <span
                class="check-value ${pass ? "pass" : "fail"}"
            >
                ${pass ? "PASS" : "FAIL"}
            </span>

        </div>
    `;
}


/* ============================================================
   DECISION
   ============================================================ */

function renderDecision(
    data,
    status,
    required
) {

    const decision =
        data.decision || {};


    const winningHash =
        data.winning_hash
        || decision.winning_hash
        || null;


    let winningGroup =
        data.winning_group;


    if (!Array.isArray(winningGroup)) {

        winningGroup =
            decision.winning_group;
    }


    if (!Array.isArray(winningGroup)) {

        winningGroup =
            deriveWinningGroup(
                data.builders || [],
                winningHash
            );
    }


    let outliers =
        data.outliers;


    if (!Array.isArray(outliers)) {

        outliers =
            decision.outliers;
    }


    if (!Array.isArray(outliers)) {

        outliers = [];
    }


    const banner =
        $("decisionBanner");


    banner.classList.remove(
        "accept",
        "reject",
        "pending"
    );


    if (status === "ACCEPT") {

        banner.classList.add(
            "accept"
        );

    } else if (
        status === "REJECT"
        || status === "ERROR"
    ) {

        banner.classList.add(
            "reject"
        );

    } else {

        banner.classList.add(
            "pending"
        );
    }


    $("decisionStatus").textContent =
        status;


    $("decisionMessage").textContent =
        data.message
        || decision.message
        || "Verification pending.";


    $("decisionQuorum").textContent =
        String(
            data.quorum
            ?? decision.quorum
            ?? 0
        );


    $("decisionRequired").textContent =
        String(required);


    $("winningGroup").textContent =
        winningGroup.length
            ? winningGroup
                .map(
                    name =>
                        name.toUpperCase()
                )
                .join(" · ")
            : "None";


    $("decisionOutliers").textContent =
        outliers.length
            ? outliers
                .map(
                    name =>
                        name.toUpperCase()
                )
                .join(" · ")
            : "None";


    $("winningHash").textContent =
        winningHash
        || "None";
}


function deriveWinningGroup(
    builders,
    winningHash
) {

    if (!winningHash) {

        return [];
    }


    return builders
        .filter(
            builder =>
                builder.verified === true
                && builder.artifact_hash
                    === winningHash
        )
        .map(
            builder =>
                builder.builder_id
        );
}


/* ============================================================
   AUDIT
   ============================================================ */

async function loadAuditStatus() {

    try {

        const data =
            await apiFetch(
                "/audit/status"
            );


        latestAudit =
            data;


        renderAuditSummary(
            data
        );


        return data;


    } catch {

        renderAuditSummary({

            valid: false,

            status: "ERROR",

            message:
                "Audit status unavailable.",

            events: 0

        });


        return null;
    }
}


function renderAuditSummary(
    audit
) {

    const valid =
        audit.valid === true;


    if ($("auditState")) {

        $("auditState").textContent =
            valid
                ? "VALID"
                : "ALERT";
    }


    if ($("auditHint")) {

        $("auditHint").textContent =
            valid
                ? "Hash chain intact"
                : (
                    audit.message
                    || "Audit chain requires attention"
                );
    }


    const panel =
        $("auditStatePanel");


    if (!panel) {

        return;
    }


    panel.classList.remove(
        "valid",
        "tampered"
    );


    if (valid) {

        panel.classList.add(
            "valid"
        );


        panel.innerHTML =
            "✓ Audit chain integrity verified · "
            + escapeHtml(
                audit.message
                || "Audit log is valid."
            );

    } else {

        panel.classList.add(
            "tampered"
        );


        panel.innerHTML =
            "⚠ Audit chain requires attention · "
            + escapeHtml(
                audit.message
                || "Audit status unavailable."
            );
    }
}


async function loadAuditEntries() {

    try {

        const data =
            await apiFetch(
                "/audit/entries?limit=10"
            );


        renderAuditEntries(
            data.entries || []
        );

    } catch {

        if ($("auditEntries")) {

            $("auditEntries").innerHTML =
                `<div class="empty-state">
                    Audit events unavailable.
                 </div>`;
        }
    }
}


function renderAuditEntries(
    entries
) {

    const container =
        $("auditEntries");


    if (!container) {

        return;
    }


    if (!entries.length) {

        container.innerHTML =
            `<div class="empty-state">
                Audit events will appear after
                a verification run.
             </div>`;

        return;
    }


    container.innerHTML =
        entries
            .map(
                entry => {

                    const hash =
                        entry.entry_hash
                        || "—";


                    return `

                        <article class="audit-entry">

                            <div class="audit-entry-top">

                                <div class="audit-event">

                                    ${escapeHtml(
                                        entry.event
                                        || "EVENT"
                                    )}

                                </div>


                                <div class="audit-time">

                                    ${escapeHtml(
                                        formatTime(
                                            entry.timestamp
                                        )
                                    )}

                                </div>

                            </div>


                            <div class="audit-entry-bottom">

                                <div class="audit-chain">
                                    CHAINED
                                </div>


                                <div class="audit-hash">

                                    ${escapeHtml(
                                        shortHash(hash)
                                    )}

                                </div>

                            </div>

                        </article>

                    `;
                }
            )
            .join("");
}


/* ============================================================
   ERROR
   ============================================================ */

function renderError(
    error
) {

    setConnectionState(
        false,
        "API error"
    );


    $("systemStatus").textContent =
        "Unavailable";


    $("systemStatus").className =
        "system-status failed";


    $("systemStatusText").textContent =
        error.message
        || "Unable to contact verification API";


    $("footerApiStatus").textContent =
        "API error";


    $("decisionBanner").classList.remove(
        "accept",
        "pending"
    );


    $("decisionBanner").classList.add(
        "reject"
    );


    $("decisionStatus").textContent =
        "ERROR";


    $("decisionMessage").textContent =
        error.message
        || "Verification failed.";
}


/* ============================================================
   BUTTON STATE
   ============================================================ */

function setButtonsBusy(
    busy,
    label
) {

    const buttons = [

        $("verifyBtn"),

        $("verifyAgainBtn"),

        $("demoBtn"),

        $("builderRefreshBtn")
    ];


    buttons.forEach(
        button => {

            if (!button) {
                return;
            }


            button.disabled =
                busy;
        }
    );


    if ($("verifyBtn")) {

        $("verifyBtn").textContent =
            busy
                ? label
                : "↻ Run verification";
    }
}


/* ============================================================
   TABS
   ============================================================ */

function setupTabs() {

    document
        .querySelectorAll(
            ".nav-item"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        document
                            .querySelectorAll(
                                ".nav-item"
                            )
                            .forEach(
                                item =>
                                    item.classList.remove(
                                        "active"
                                    )
                            );


                        button.classList.add(
                            "active"
                        );


                        document
                            .querySelectorAll(
                                ".tab-content"
                            )
                            .forEach(
                                tab =>
                                    tab.classList.remove(
                                        "active"
                                    )
                            );


                        const tabId =
                            button.dataset.tab;


                        const target =
                            $(
                                `tab-${tabId}`
                            );


                        if (target) {

                            target.classList.add(
                                "active"
                            );
                        }
                    }
                );
            }
        );
}


/* ============================================================
   EVENTS
   ============================================================ */

function setupEvents() {

    if ($("verifyBtn")) {

        $("verifyBtn").addEventListener(
            "click",
            runVerification
        );
    }


    if ($("verifyAgainBtn")) {

        $("verifyAgainBtn").addEventListener(
            "click",
            runVerification
        );
    }


    if ($("builderRefreshBtn")) {

        $("builderRefreshBtn").addEventListener(
            "click",
            runVerification
        );
    }


    if ($("auditRefreshBtn")) {

        $("auditRefreshBtn").addEventListener(
            "click",
            async () => {

                await loadAuditStatus();

                await loadAuditEntries();
            }
        );
    }
}


/* ============================================================
   INITIALIZE
   ============================================================ */

async function initialize() {

    setupTabs();

    setupSourceInput();

    setupEvents();


    const online =
        await checkHealth();


    if (!online) {

        return;
    }


    await runVerification();

    await loadAuditStatus();

    await loadAuditEntries();
}


/* ============================================================
   START
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    initialize
);