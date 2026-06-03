import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { api } from '../api';
const TOOL_TITLE = {
    advance_claim: 'Claim decision',
    create_nudge_campaign: 'Draft nudge campaign',
    save_view: 'Save view',
};
const TOOL_ICON = {
    advance_claim: '✓',
    create_nudge_campaign: '✉',
    save_view: '★',
};
export default function ToolPreviewCard({ tool, args }) {
    const [status, setStatus] = useState('idle');
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    async function confirm() {
        setStatus('running');
        setError(null);
        try {
            if (tool === 'advance_claim') {
                const r = await api.advanceClaim(args.claim_id, args.decision, args.note, args.rejection_code);
                setResult(`${r.claim_id} → ${r.status}`);
            }
            else if (tool === 'create_nudge_campaign') {
                const r = await api.createNudgeCampaign(args.template_id, args.dealer_ids ?? [], args.deadline, args.notes);
                setResult(`Drafted ${r.campaign_code ?? r.campaign_id.slice(0, 8)} (${r.recipient_count} recipients)`);
            }
            else if (tool === 'save_view') {
                const r = await api.saveView(args.name, args.filter_payload ?? {}, args.description, args.pinned);
                setResult(`Saved as '${r.name}'`);
            }
            else {
                throw new Error(`Unknown tool: ${tool}`);
            }
            setStatus('done');
        }
        catch (e) {
            setError(String(e));
            setStatus('error');
        }
    }
    function cancel() {
        setStatus('done');
        setResult('Cancelled.');
    }
    const title = TOOL_TITLE[tool] ?? tool;
    const icon = TOOL_ICON[tool] ?? '⚙';
    return (_jsxs("div", { className: "tool-preview", children: [_jsxs("div", { className: "tool-preview-head", children: [_jsx("span", { className: "tool-preview-icon", children: icon }), _jsx("span", { className: "tool-preview-title", children: title }), _jsx("span", { className: "tool-preview-badge", children: "action" })] }), _jsx("table", { className: "tool-preview-args", children: _jsx("tbody", { children: Object.entries(args).map(([k, v]) => (_jsxs("tr", { children: [_jsx("td", { className: "tool-preview-key", children: k }), _jsx("td", { className: "tool-preview-val", children: Array.isArray(v) ? v.join(', ') : typeof v === 'object' && v !== null
                                    ? JSON.stringify(v)
                                    : String(v) })] }, k))) }) }), status === 'idle' && (_jsxs("div", { className: "tool-preview-actions", children: [_jsx("button", { className: "primary", onClick: confirm, children: "Confirm" }), _jsx("button", { onClick: cancel, children: "Cancel" })] })), status === 'running' && _jsx("div", { className: "tool-preview-status", children: "Executing\u2026" }), status === 'done' && result && _jsxs("div", { className: "tool-preview-status done", children: ["\u2713 ", result] }), status === 'error' && error && _jsxs("div", { className: "tool-preview-status err", children: ["\u2717 ", error] })] }));
}
