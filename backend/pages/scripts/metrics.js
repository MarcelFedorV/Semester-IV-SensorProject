// ── Fishing tabs ──────────────────────────────────────────────────────────────
let currentTab   = 'me';
let currentSFTab = 'me';

async function loadMyStats() {
    try {
        const res = await fetch('/api/stats/me');
        if (!res.ok) return;
        const data = await res.json();
        const f = data.fishing;

        document.getElementById('stat-catches').textContent     = f.total_catches;
        document.getElementById('stat-unique').textContent      = f.unique_fish;
        document.getElementById('stat-distance').textContent    = f.total_distance_km + ' km';
        document.getElementById('stat-sessions').textContent    = f.total_sessions;
        document.getElementById('stat-achievements').textContent = f.achievements;

        // SpaceFunk personal stats come from the same endpoint
        const sf = data.spacefunk;
        if (sf) {
            document.getElementById('sf-stat-runs').textContent     = sf.total_runs;
            document.getElementById('sf-stat-score').textContent    = sf.best_score;
            document.getElementById('sf-stat-distance').textContent = sf.total_distance_km + ' km';
        }
    } catch (e) {
        console.error('Failed to load my stats', e);
    }
}

async function loadGlobalStats() {
    try {
        const res = await fetch('/api/stats/global');
        if (!res.ok) return;
        const data = await res.json();

        // Fishing global table
        const tbody = document.getElementById('global-tbody');
        tbody.innerHTML = '';
        data.forEach(player => {
            tbody.innerHTML += `
                <tr>
                    <td>${player.username}</td>
                    <td>${player.total_catches}</td>
                    <td>${player.unique_fish}</td>
                    <td>${player.total_distance_km} km</td>
                </tr>`;
        });

        // SpaceFunk leaderboard — sort by best score descending
        const sfSorted = [...data].sort((a, b) => b.sf_best_score - a.sf_best_score);
        const sfTbody  = document.getElementById('sf-global-tbody');
        sfTbody.innerHTML = '';
        sfSorted.forEach(player => {
            if (player.sf_best_score === 0 && player.sf_total_distance_km === 0) return;
            sfTbody.innerHTML += `
                <tr>
                    <td>${player.username}</td>
                    <td>${player.sf_best_score}</td>
                    <td>${player.sf_total_distance_km} km</td>
                </tr>`;
        });
    } catch (e) {
        console.error('Failed to load global stats', e);
    }
}

// ── Tab switchers ─────────────────────────────────────────────────────────────
function switchTab(tab) {
    currentTab = tab;
    document.getElementById('tab-me').classList.toggle('active',     tab === 'me');
    document.getElementById('tab-global').classList.toggle('active', tab === 'global');
    document.getElementById('panel-me').classList.toggle('active',     tab === 'me');
    document.getElementById('panel-global').classList.toggle('active', tab === 'global');
}

function switchSFTab(tab) {
    currentSFTab = tab;
    document.getElementById('sf-tab-me').classList.toggle('active',     tab === 'me');
    document.getElementById('sf-tab-global').classList.toggle('active', tab === 'global');
    document.getElementById('sf-panel-me').classList.toggle('active',     tab === 'me');
    document.getElementById('sf-panel-global').classList.toggle('active', tab === 'global');
}

// ── Boot ──────────────────────────────────────────────────────────────────────
loadMyStats();
loadGlobalStats();
setInterval(() => { loadMyStats(); loadGlobalStats(); }, 5000);
