let currentTab = 'me';

async function loadMyStats() {
    try {
        const res = await fetch('/api/stats/me');
        if (!res.ok) return;
        const data = await res.json();
        const f = data.fishing;

        document.getElementById('stat-catches').textContent = f.total_catches;
        document.getElementById('stat-unique').textContent = f.unique_fish;
        document.getElementById('stat-distance').textContent = f.total_distance_km + ' km';
        document.getElementById('stat-sessions').textContent = f.total_sessions;
        document.getElementById('stat-achievements').textContent = f.achievements;
    } catch (e) {
        console.error('Failed to load my stats', e);
    }
}

async function loadGlobalStats() {
    try {
        const res = await fetch('/api/stats/global');
        if (!res.ok) return;
        const data = await res.json();

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
    } catch (e) {
        console.error('Failed to load global stats', e);
    }
}

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
    document.getElementById('panel-' + tab).classList.add('active');
}

function refresh() {
    if (currentTab === 'me') loadMyStats();
    else loadGlobalStats();
}

// it loads the stats first and then every 5 seconds
loadMyStats();
loadGlobalStats();
setInterval(refresh, 5000);