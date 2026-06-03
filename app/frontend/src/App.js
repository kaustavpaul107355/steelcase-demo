import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { api, personaStore } from './api';
import Chat from './components/Chat';
import Home from './components/Home';
import PersonaSwitcher from './components/PersonaSwitcher';
import RightPane from './components/RightPane';
export default function App() {
    const [me, setMe] = useState(null);
    const [config, setConfig] = useState(null);
    const [error, setError] = useState(null);
    const [personaEmail, setPersonaEmail] = useState(() => personaStore.get());
    function loadIdentity() {
        setMe(null);
        setError(null);
        Promise.all([api.me(), api.config()])
            .then(([m, c]) => {
            setMe(m);
            setConfig(c);
        })
            .catch((e) => setError(String(e)));
    }
    useEffect(loadIdentity, [personaEmail]);
    function onPersonaChange(email) {
        personaStore.set(email);
        setPersonaEmail(email);
    }
    if (error) {
        return (_jsxs("div", { className: "app-shell", children: [_jsx(Header, { me: null, mode: null, config: null, onPersonaChange: onPersonaChange }), _jsx("div", { className: "pane-body", children: _jsxs("div", { className: "coachmark", children: ["Backend unreachable. ", _jsx("pre", { children: error })] }) })] }));
    }
    if (!me || !config) {
        return (_jsxs("div", { className: "app-shell", children: [_jsx(Header, { me: null, mode: null, config: null, onPersonaChange: onPersonaChange }), _jsx("div", { className: "pane-body", children: _jsx("div", { className: "empty", children: "Loading\u2026" }) })] }));
    }
    return (_jsxs("div", { className: "app-shell", children: [_jsx(Header, { me: me, mode: config.mode, config: config, onPersonaChange: onPersonaChange }), _jsx(Home, { reloadKey: `${me.email}:${me.role}` }), _jsxs("div", { className: "body", children: [_jsx(Chat, {}), _jsx(RightPane, { me: me, config: config })] })] }));
}
function Header({ me, mode, config, onPersonaChange }) {
    return (_jsxs("div", { className: "header", children: [_jsxs("span", { className: "brand", children: [_jsx("span", { className: "brand-mark" }), "COMPASS", _jsx("small", { children: "Co-op Program Analytics Agent" })] }), _jsx("span", { className: "spacer" }), mode && _jsxs("span", { className: `badge mode-${mode}`, children: ["mode: ", mode] }), me && (_jsxs(_Fragment, { children: [_jsx("span", { className: `badge role role-${me.role}`, children: me.role }), me.region_id && _jsx("span", { className: "badge region", children: me.region_id }), me.dealer_id && _jsx("span", { className: "badge dealer", children: me.dealer_id })] })), config?.allow_persona_switch && me && (_jsx(PersonaSwitcher, { currentEmail: me.email, onChange: onPersonaChange })), !config?.allow_persona_switch && me && (_jsx("span", { className: "muted-name", children: me.display_name }))] }));
}
