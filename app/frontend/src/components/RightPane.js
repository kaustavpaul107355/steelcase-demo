import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { api, } from '../api';
// Per-role default tab + visible set. Director/Finance get a read-only tour;
// dealers see only saved views; channel_mgr/rmd see the full workbench.
const ROLE_TABS = {
    channel_mgr: ['approvals', 'nudges', 'saved_views'],
    rmd: ['approvals', 'nudges', 'saved_views'],
    director: ['approvals', 'saved_views'],
    finance: ['approvals', 'saved_views'],
    dealer: ['saved_views'],
    guest: ['saved_views'],
};
export default function RightPane({ me, config }) {
    const visibleTabs = (ROLE_TABS[me.role] ?? ROLE_TABS.guest).filter((t) => {
        if (t === 'approvals')
            return true; // gated below by feature flag
        if (t === 'nudges')
            return true;
        return true;
    });
    const allTabs = [
        { id: 'approvals', label: 'Approval Queue', gate: 'approvals', phase: 'Phase 5 (Lakebase)' },
        { id: 'nudges', label: 'Nudges', gate: 'nudges', phase: 'Phase 5 (Lakebase)' },
        { id: 'saved_views', label: 'Saved Views', gate: 'saved_views', phase: '—' },
    ];
    const tabs = allTabs.filter((t) => visibleTabs.includes(t.id));
    const firstEnabled = tabs.find((t) => config.features[t.gate])?.id ?? tabs[0]?.id ?? 'saved_views';
    const [active, setActive] = useState(firstEnabled);
    // Reset to first available tab when the visible set changes (persona switch).
    useEffect(() => setActive(firstEnabled), [me.role]);
    const readOnly = me.role === 'director' || me.role === 'finance' || me.role === 'dealer';
    return (_jsxs("div", { className: "pane workbench-pane", children: [_jsxs("div", { className: "pane-header", children: ["Workbench", readOnly && _jsx("span", { className: "readonly-badge", children: "read-only" })] }), _jsx("div", { className: "tabs", children: tabs.map((t) => {
                    const enabled = config.features[t.gate];
                    return (_jsx("div", { className: `tab ${active === t.id ? 'active' : ''} ${enabled ? '' : 'disabled'}`, onClick: () => enabled && setActive(t.id), children: t.label }, t.id));
                }) }), _jsxs("div", { className: "pane-body", children: [active === 'approvals' &&
                        (config.features.approvals ? (_jsx(Approvals, { readOnly: readOnly })) : (_jsx(CoachmarkDisabled, { phase: "Phase 5 (Lakebase)", mode: config.mode }))), active === 'nudges' &&
                        (config.features.nudges ? (_jsx(Nudges, { readOnly: readOnly })) : (_jsx(CoachmarkDisabled, { phase: "Phase 5 (Lakebase)", mode: config.mode }))), active === 'saved_views' && (_jsx(SavedViews, { persistent: config.features.saved_views_persistent }))] })] }));
}
function CoachmarkDisabled({ phase, mode }) {
    return (_jsxs("div", { className: "coachmark", children: ["This tab requires ", _jsx("strong", { children: phase }), ". Currently running in ", _jsx("code", { children: mode }), "."] }));
}
function Approvals({ readOnly }) {
    const [rows, setRows] = useState(null);
    const [err, setErr] = useState(null);
    useEffect(() => {
        api.approvals().then(setRows).catch((e) => setErr(String(e)));
    }, []);
    if (err)
        return _jsx("div", { className: "coachmark", children: err });
    if (!rows)
        return _jsx(SkeletonList, {});
    if (rows.length === 0)
        return _jsx("div", { className: "empty", children: "No pending approvals." });
    const REJECTION_CODES = [
        'MISSING_PREAPPROVAL',
        'TIER_INELIGIBLE',
        'OFF_BRAND',
        'OUT_OF_REGION',
        'DOC_INCOMPLETE',
        'DOUBLE_DIP',
        'OTHER',
    ];
    async function advance(claim_id, decision) {
        let rejection_code;
        if (decision === 'Reject') {
            const input = window.prompt(`Rejection code (one of: ${REJECTION_CODES.join(', ')})`, 'OTHER');
            if (input === null)
                return;
            rejection_code = REJECTION_CODES.includes(input) ? input : 'OTHER';
        }
        await api.advanceClaim(claim_id, decision, undefined, rejection_code);
        api.approvals().then(setRows);
    }
    return (_jsx(_Fragment, { children: rows.map((r) => (_jsxs("div", { className: "list-row", children: [_jsxs("div", { className: "row-head", children: [_jsx("span", { className: "title", children: r.claim_id }), _jsx("span", { className: "muted", children: "\u00B7" }), _jsx("span", { className: "muted", children: r.dealer_name ?? r.dealer_id }), _jsx("span", { className: `status-pill status-${r.status.toLowerCase()}`, children: r.status })] }), _jsxs("div", { className: "row-meta", children: ["created ", new Date(r.created_at).toLocaleString()] }), !readOnly && (_jsxs("div", { className: "row-actions", children: [_jsx("button", { className: "primary", onClick: () => advance(r.claim_id, 'Approve'), children: "Approve" }), _jsx("button", { className: "danger", onClick: () => advance(r.claim_id, 'Reject'), children: "Reject" })] }))] }, r.claim_id))) }));
}
function Nudges({ readOnly }) {
    const [rows, setRows] = useState(null);
    const [err, setErr] = useState(null);
    useEffect(() => {
        api.nudges().then(setRows).catch((e) => setErr(String(e)));
    }, []);
    if (err)
        return _jsx("div", { className: "coachmark", children: err });
    if (!rows)
        return _jsx(SkeletonList, {});
    if (rows.length === 0)
        return _jsx("div", { className: "empty", children: "No drafts yet. Ask the agent to generate one." });
    async function queue(id) {
        await api.queueNudge(id);
        api.nudges().then(setRows);
    }
    return (_jsx(_Fragment, { children: rows.map((r) => (_jsxs("div", { className: "list-row", children: [_jsxs("div", { className: "row-head", children: [_jsx("span", { className: "title", children: r.campaign_code ?? r.campaign_id.slice(0, 8) }), _jsx("span", { className: "muted", children: "\u00B7" }), _jsx("span", { className: "muted", children: r.template_id }), _jsx("span", { className: "muted", children: "\u00B7" }), _jsxs("span", { className: "muted", children: [r.recipient_count, " recipients"] })] }), _jsxs("div", { className: "row-meta", children: [_jsx("span", { className: `status-pill status-${r.status.toLowerCase()}`, children: r.status }), r.deadline ? ` · deadline ${r.deadline}` : ''] }), r.status === 'Draft' && !readOnly && (_jsx("div", { className: "row-actions", children: _jsx("button", { className: "primary", onClick: () => queue(r.campaign_id), children: "Queue" }) }))] }, r.campaign_id))) }));
}
function SavedViews({ persistent }) {
    const [rows, setRows] = useState(null);
    const [err, setErr] = useState(null);
    useEffect(() => {
        api.savedViews().then(setRows).catch((e) => setErr(String(e)));
    }, []);
    if (err)
        return _jsx("div", { className: "coachmark", children: err });
    if (!rows)
        return _jsx(SkeletonList, {});
    return (_jsxs(_Fragment, { children: [!persistent && (_jsx("div", { className: "coachmark", style: { marginBottom: 12 }, children: "Lite mode \u2014 saved views are not persisted to Lakebase (Phase 5)." })), rows.length === 0 && _jsx("div", { className: "empty", children: "No saved views yet." }), rows.map((r) => (_jsxs("div", { className: "list-row", children: [_jsxs("div", { className: "row-head", children: [_jsx("span", { className: "title", children: r.name }), r.pinned && _jsx("span", { className: "badge", children: "pinned" })] }), r.description && _jsx("div", { className: "row-meta", children: r.description })] }, r.view_id)))] }));
}
function SkeletonList() {
    return (_jsx(_Fragment, { children: [0, 1, 2].map((i) => (_jsxs("div", { className: "list-row skeleton-row", children: [_jsx("div", { className: "skeleton-text wide" }), _jsx("div", { className: "skeleton-text narrow" })] }, i))) }));
}
