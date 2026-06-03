import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { api } from '../api';
export default function Home({ reloadKey }) {
    const [home, setHome] = useState(null);
    const [err, setErr] = useState(null);
    useEffect(() => {
        setHome(null);
        setErr(null);
        api.home().then(setHome).catch((e) => setErr(String(e)));
    }, [reloadKey]);
    if (err) {
        return (_jsx("div", { className: "home", children: _jsxs("div", { className: "coachmark", children: ["Home failed to load: ", err] }) }));
    }
    if (!home) {
        return (_jsxs("div", { className: "home", children: [_jsxs("div", { className: "home-header", children: [_jsx("div", { className: "home-headline skeleton-text wide" }), _jsx("div", { className: "home-scope skeleton-text narrow" })] }), _jsx("div", { className: "kpi-row", children: [0, 1, 2, 3].map((i) => (_jsx("div", { className: "kpi-tile skeleton" }, i))) })] }));
    }
    return (_jsxs("div", { className: "home", children: [_jsxs("div", { className: "home-header", children: [_jsx("div", { className: "home-headline", children: home.headline }), _jsxs("div", { className: "home-scope", children: ["Scope: ", home.scope_label] })] }), _jsx("div", { className: "kpi-row", children: home.tiles.map((t) => (_jsx(KpiCard, { tile: t }, t.key))) }), home.rows.length > 0 && (_jsxs("div", { className: "home-rows", children: [_jsx("div", { className: "home-rows-header", children: "Drill-in" }), home.rows.map((r, i) => (_jsxs("div", { className: `home-row intent-${r.intent}`, children: [_jsx("span", { className: "home-row-primary", children: r.primary }), r.secondary && _jsx("span", { className: "home-row-secondary", children: r.secondary }), r.metric && _jsx("span", { className: "home-row-metric", children: r.metric })] }, i)))] }))] }));
}
function KpiCard({ tile }) {
    return (_jsxs("div", { className: `kpi-tile intent-${tile.intent}`, children: [_jsx("div", { className: "kpi-label", children: tile.label }), _jsx("div", { className: "kpi-value", children: formatValue(tile) }), tile.sub_label && _jsx("div", { className: "kpi-sub", children: tile.sub_label })] }));
}
function formatValue(tile) {
    const v = tile.value;
    if (v == null)
        return '—';
    if (tile.format === 'currency' && typeof v === 'number')
        return formatCurrency(v);
    if (tile.format === 'percent' && typeof v === 'number')
        return `${v.toFixed(1)}%`;
    if (tile.format === 'count' && typeof v === 'number')
        return v.toLocaleString();
    return String(v);
}
function formatCurrency(v) {
    if (Math.abs(v) >= 1_000_000)
        return `$${(v / 1_000_000).toFixed(2)}M`;
    if (Math.abs(v) >= 10_000)
        return `$${(v / 1000).toFixed(0)}K`;
    if (Math.abs(v) >= 1000)
        return `$${(v / 1000).toFixed(1)}K`;
    return `$${v.toLocaleString()}`;
}
