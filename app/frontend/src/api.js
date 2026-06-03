/* Tiny typed fetch client for the COMPASS BFF. */
const PERSONA_KEY = 'compass.persona.email';
export const personaStore = {
    get() {
        try {
            return localStorage.getItem(PERSONA_KEY);
        }
        catch {
            return null;
        }
    },
    set(email) {
        try {
            if (email)
                localStorage.setItem(PERSONA_KEY, email);
            else
                localStorage.removeItem(PERSONA_KEY);
        }
        catch { /* no-op */ }
    },
};
async function http(input, init) {
    const headers = {
        'Content-Type': 'application/json',
        ...(init?.headers || {}),
    };
    const persona = personaStore.get();
    if (persona)
        headers['X-Compass-As-User'] = persona;
    const res = await fetch(input, {
        credentials: 'same-origin',
        headers,
        ...init,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status} ${res.statusText}: ${text}`);
    }
    return (await res.json());
}
export const api = {
    me: () => http('/api/me'),
    config: () => http('/api/config'),
    personas: () => http('/api/personas'),
    home: () => http('/api/home'),
    latestSession: () => http('/api/session/latest'),
    chat: (message, session_id, route_hint) => http('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message, session_id, route_hint }),
    }),
    approvals: () => http('/api/approvals'),
    advanceClaim: (claim_id, decision, note, rejection_code) => http(`/api/approvals/${encodeURIComponent(claim_id)}/advance`, { method: 'POST', body: JSON.stringify({ decision, note, rejection_code }) }),
    nudges: () => http('/api/nudge-campaigns'),
    createNudgeCampaign: (template_id, dealer_ids, deadline, notes) => http('/api/nudge-campaigns', {
        method: 'POST',
        body: JSON.stringify({ template_id, dealer_ids, deadline, notes }),
    }),
    queueNudge: (campaign_id) => http(`/api/nudge-campaigns/${encodeURIComponent(campaign_id)}/queue`, {
        method: 'POST',
    }),
    savedViews: () => http('/api/saved-views'),
    saveView: (name, filter_payload, description, pinned) => http('/api/saved-views', {
        method: 'POST',
        body: JSON.stringify({ name, filter_payload, description, pinned: !!pinned }),
    }),
};
