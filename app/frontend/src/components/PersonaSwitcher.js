import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
const ROLE_LABEL = {
    channel_mgr: 'Channel Mgr',
    director: 'Director',
    rmd: 'RMD',
    finance: 'Finance',
    dealer: 'Dealer',
    guest: 'Guest',
};
export default function PersonaSwitcher({ currentEmail, onChange }) {
    const [open, setOpen] = useState(false);
    const [personas, setPersonas] = useState(null);
    const [err, setErr] = useState(null);
    const ref = useRef(null);
    useEffect(() => {
        api.personas().then(setPersonas).catch((e) => setErr(String(e)));
    }, []);
    useEffect(() => {
        function onDocClick(e) {
            if (!ref.current)
                return;
            if (!ref.current.contains(e.target))
                setOpen(false);
        }
        if (open)
            document.addEventListener('mousedown', onDocClick);
        return () => document.removeEventListener('mousedown', onDocClick);
    }, [open]);
    const current = personas?.find((p) => p.email === currentEmail);
    const label = current ? current.display_name : 'Sign in';
    return (_jsxs("div", { className: "persona-switcher", ref: ref, children: [_jsxs("button", { className: "persona-switcher-trigger", onClick: () => setOpen((o) => !o), "aria-expanded": open, children: [_jsx("span", { className: "persona-avatar", children: initials(label) }), _jsxs("span", { className: "persona-label", children: [_jsx("span", { className: "persona-name", children: label }), current && (_jsxs("span", { className: "persona-sub", children: [ROLE_LABEL[current.role] ?? current.role, current.region_id ? ` · ${current.region_id}` : ''] }))] }), _jsx("span", { className: "persona-caret", children: "\u25BE" })] }), open && (_jsxs("div", { className: "persona-menu", children: [_jsx("div", { className: "persona-menu-header", children: "Act as\u2026" }), err && _jsx("div", { className: "persona-menu-err", children: err }), !personas && !err && _jsx("div", { className: "persona-menu-empty", children: "Loading\u2026" }), personas && personas.length === 0 && (_jsx("div", { className: "persona-menu-empty", children: "No personas seeded." })), personas?.map((p) => (_jsxs("button", { className: `persona-row ${p.email === currentEmail ? 'active' : ''}`, onClick: () => {
                            onChange(p.email);
                            setOpen(false);
                        }, children: [_jsx("span", { className: "persona-avatar small", children: initials(p.display_name) }), _jsxs("span", { className: "persona-row-text", children: [_jsx("span", { className: "persona-row-name", children: p.display_name }), _jsxs("span", { className: "persona-row-sub", children: [_jsx("span", { className: `role-chip role-${p.role}`, children: ROLE_LABEL[p.role] ?? p.role }), p.region_id && _jsx("span", { className: "region-chip", children: p.region_id }), p.dealer_id && _jsx("span", { className: "dealer-chip", children: p.dealer_id })] })] })] }, p.user_id)))] }))] }));
}
function initials(name) {
    return name
        .split(/\s+/)
        .map((p) => p[0])
        .filter(Boolean)
        .slice(0, 2)
        .join('')
        .toUpperCase();
}
