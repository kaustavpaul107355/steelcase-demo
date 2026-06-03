import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import ToolPreviewCard from './ToolPreviewCard';
const TABS = [
    {
        id: 'auto',
        label: 'Auto',
        blurb: 'Router picks Genie or the Handbook based on your question.',
        starters: [
            "What's my Q4 forfeiture risk?",
            'Top 5 activity types by revenue per co-op dollar in AMER',
            'Can a Silver-tier dealer submit a $25K digital ad claim?',
        ],
    },
    {
        id: 'genie_util',
        label: 'Co-op Utilization & Risk',
        blurb: 'Quantitative — Genie space backed by `coop_program_metrics` + `forfeiture_risk`.',
        starters: [
            'Which AMER East dealers have unused balance > $40K?',
            'FY26 forfeiture risk by region',
            'Top 10 dealers by utilization rate this quarter',
        ],
    },
    {
        id: 'genie_marketing',
        label: 'Marketing Effectiveness',
        blurb: 'Quantitative — Genie space for activity ROI and lift.',
        starters: [
            'Best-performing activity types by revenue per co-op dollar',
            'Programmatic display lift YoY',
            'Which campaigns drove the most sell-through in AMER?',
        ],
    },
    {
        id: 'ka',
        label: 'Handbook (KA)',
        blurb: 'Policy — Agent Bricks Knowledge Assistant over the co-op program handbook.',
        starters: [
            'Can a Silver-tier dealer submit a $25K digital ad claim?',
            'What documentation do I need for an event claim?',
            'How does pre-approval work for over-$10K claims?',
        ],
    },
];
const emptyState = () => ({ sessionId: undefined, turns: [], userTurns: [] });
export default function Chat() {
    const [activeTab, setActiveTab] = useState('auto');
    const [sessions, setSessions] = useState({
        auto: emptyState(),
        genie_util: emptyState(),
        genie_marketing: emptyState(),
        ka: emptyState(),
    });
    const [draft, setDraft] = useState('');
    const [pending, setPending] = useState(false);
    const tab = useMemo(() => TABS.find((t) => t.id === activeTab), [activeTab]);
    const state = sessions[activeTab];
    async function send(message) {
        const m = message.trim();
        if (!m || pending)
            return;
        setDraft('');
        setSessions((s) => ({
            ...s,
            [activeTab]: { ...s[activeTab], userTurns: [...s[activeTab].userTurns, m] },
        }));
        setPending(true);
        try {
            const turn = await api.chat(m, state.sessionId, activeTab);
            setSessions((s) => ({
                ...s,
                [activeTab]: {
                    sessionId: turn.session_id,
                    userTurns: s[activeTab].userTurns,
                    turns: [...s[activeTab].turns, turn],
                },
            }));
        }
        catch (e) {
            setSessions((s) => ({
                ...s,
                [activeTab]: {
                    ...s[activeTab],
                    turns: [
                        ...s[activeTab].turns,
                        {
                            session_id: s[activeTab].sessionId || '',
                            turn_index: s[activeTab].turns.length,
                            route: 'error',
                            content: `Request failed: ${e}`,
                            citations: [],
                        },
                    ],
                },
            }));
        }
        finally {
            setPending(false);
        }
    }
    const items = [];
    const max = Math.max(state.userTurns.length, state.turns.length);
    for (let i = 0; i < max; i++) {
        if (state.userTurns[i] !== undefined)
            items.push({ role: 'user', content: state.userTurns[i] });
        if (state.turns[i] !== undefined)
            items.push({ role: 'assistant', content: state.turns[i].content, turn: state.turns[i] });
    }
    return (_jsxs("div", { className: "pane chat-pane", children: [_jsx("div", { className: "chat-tabs", children: TABS.map((t) => (_jsxs("button", { className: `chat-tab ${activeTab === t.id ? 'active' : ''}`, onClick: () => setActiveTab(t.id), children: [_jsx("span", { className: "chat-tab-label", children: t.label }), sessions[t.id].turns.length > 0 && (_jsx("span", { className: "chat-tab-count", children: sessions[t.id].turns.length }))] }, t.id))) }), _jsx("div", { className: "chat-blurb", children: tab.blurb }), _jsxs("div", { className: "pane-body chat-body", children: [items.length === 0 && (_jsxs("div", { className: "chat-empty", children: [_jsx("div", { className: "chat-empty-title", children: "Try a starter:" }), _jsx("div", { className: "starter-row", children: tab.starters.map((s) => (_jsx("button", { className: "starter-chip", onClick: () => send(s), children: s }, s))) })] })), _jsxs("div", { className: "chat-list", children: [items.map((it, i) => (_jsxs("div", { className: `bubble ${it.role}`, children: [_jsx("div", { className: "bubble-content", children: it.content }), it.turn && _jsx(TurnExtras, { turn: it.turn })] }, i))), pending && _jsx(PendingBubble, {})] })] }), _jsxs("div", { className: "composer", children: [_jsx("textarea", { value: draft, onChange: (e) => setDraft(e.target.value), onKeyDown: (e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                send(draft);
                            }
                        }, placeholder: activeTab === 'ka'
                            ? 'Ask a policy or eligibility question…'
                            : activeTab === 'auto'
                                ? 'Ask anything — utilization, ROI, or policy.'
                                : 'Ask a quantitative question…', disabled: pending }), _jsx("button", { onClick: () => send(draft), disabled: pending || !draft.trim(), children: "Send" })] })] }));
}
function PendingBubble() {
    const [elapsed, setElapsed] = useState(0);
    useEffect(() => {
        const t = setInterval(() => setElapsed((s) => s + 1), 1000);
        return () => clearInterval(t);
    }, []);
    const hint = elapsed < 8
        ? 'Thinking…'
        : elapsed < 20
            ? 'Calling Genie / KA — typically 15–25 s.'
            : elapsed < 45
                ? 'Cold warehouse — first Genie query can take ~40 s.'
                : 'Still working… check app logs if this exceeds 60 s.';
    return (_jsxs("div", { className: "bubble assistant pending", children: [_jsx("div", { className: "bubble-shimmer" }), _jsx("div", { className: "bubble-content", children: hint }), _jsxs("div", { className: "bubble-elapsed", children: [elapsed, "s"] })] }));
}
function TurnExtras({ turn }) {
    return (_jsxs(_Fragment, { children: [turn.tool_preview && (_jsx(ToolPreviewCard, { tool: turn.tool_preview.tool, args: turn.tool_preview.args ?? {} })), turn.citations.length > 0 && (_jsx("div", { className: "citations", children: turn.citations.map((c) => (_jsxs("span", { className: "citation", title: c.excerpt ?? '', children: [_jsx("span", { className: "citation-dot" }), c.doc_id, c.section ? ' ' + c.section : ''] }, c.doc_id + (c.section ?? '')))) })), turn.genie && (turn.genie.query || (turn.genie.rows && turn.genie.rows.length > 0)) && (_jsxs("details", { className: "metric-sql", children: [_jsx("summary", { children: "Show metric & SQL" }), turn.genie.query && _jsx("pre", { className: "sql", children: turn.genie.query }), turn.genie.rows && turn.genie.columns && (_jsxs("table", { className: "result-table", children: [_jsx("thead", { children: _jsx("tr", { children: turn.genie.columns.map((c) => (_jsx("th", { children: c }, c))) }) }), _jsx("tbody", { children: turn.genie.rows.slice(0, 20).map((r, i) => (_jsx("tr", { children: turn.genie.columns.map((c) => (_jsx("td", { children: String(r[c] ?? '') }, c))) }, i))) })] }))] })), turn.latency_ms != null && (_jsxs("div", { className: "turn-meta", children: [_jsx("span", { className: `route-pill route-${turn.route}`, children: turn.route }), _jsxs("span", { children: ["\u00B7 ", turn.latency_ms, " ms"] }), turn.trace_id && _jsxs("span", { children: ["\u00B7 trace ", turn.trace_id.slice(0, 12), "\u2026"] })] }))] }));
}
