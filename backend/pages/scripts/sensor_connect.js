// ── Constants ────────────────────────────────────────────────────────────────
const CSC_SERVICE     = '00001816-0000-1000-8000-00805f9b34fb';
const CSC_MEASUREMENT = '00002a5b-0000-1000-8000-00805f9b34fb';

// ── CSCMetrics — port of sensor_device/metrics.py ───────────────────────────
const WHEEL_CIRCUMFERENCE = 2.1;   // metres, 700c × 25mm tyre
const GEAR_RATIO          = 2.8;   // wheel revs per crank rev
const TIME_RESOLUTION     = 1024;  // ticks per second
const STOP_TIMEOUT_MS     = 2000;  // ms of silence before declaring stopped

class CSCMetrics {
    constructor() {
        this._lastWheelRevs = null;
        this._lastWheelTime = null;
        this._lastCrankRevs = null;
        this._lastCrankTime = null;
        this.distanceM  = 0;
        this.speedMs    = 0;
        this.cadenceRpm = 0;
        this._frozenCount = 0;
        this._lastRevKey  = null;
    }

    update(dataView) {
        const flags    = dataView.getUint8(0);
        let   offset   = 1;
        const hasWheel = !!(flags & 0x01);
        const hasCrank = !!(flags & 0x02);

        // Read raw cumulative counters to detect if wheel/crank actually moved
        let revKey = null;
        if (hasWheel && dataView.byteLength >= offset + 6)
            revKey = dataView.getUint32(offset, true) + ':' + dataView.getUint32(offset, true);
        else if (hasCrank && dataView.byteLength >= (hasWheel ? offset + 6 + 4 : offset + 4))
            revKey = 'c:' + dataView.getUint16(hasWheel ? offset + 6 : offset, true);

        if (revKey !== null && revKey === this._lastRevKey) {
            this._frozenCount++;
            if (this._frozenCount >= 2) {
                this.speedMs    = 0;
                this.cadenceRpm = 0;
            }
        } else {
            this._frozenCount = 0;
            this._lastRevKey  = revKey;
        }

        if (hasWheel && dataView.byteLength >= offset + 6)
            offset = this._parseWheel(dataView, offset);

        if (hasCrank && dataView.byteLength >= offset + 4)
            this._parseCrank(dataView, offset, !hasWheel);

        return this._snapshot();
    }

    _parseWheel(dv, offset) {
        const wheelRevs = dv.getUint32(offset,     true);
        const wheelTime = dv.getUint16(offset + 4, true);

        if (this._lastWheelRevs !== null) {
            const dRevs = (wheelRevs - this._lastWheelRevs) >>> 0;
            const dTime = (wheelTime - this._lastWheelTime) & 0xFFFF;
            if (dRevs > 0 && dTime > 0) {
                // Actual new revolution — update speed and distance
                const s    = dTime / TIME_RESOLUTION;
                const dist = dRevs * WHEEL_CIRCUMFERENCE;
                this.distanceM += dist;
                this.speedMs    = dist / s;
            }
            // Frozen packet (dRevs=0 or dTime=0): keep last speed.
            // The interval's distance-freeze detection will zero it if truly stopped.
        }
        this._lastWheelRevs = wheelRevs;
        this._lastWheelTime = wheelTime;
        return offset + 6;
    }

    _parseCrank(dv, offset, deriveSpeed) {
        const crankRevs = dv.getUint16(offset,     true);
        const crankTime = dv.getUint16(offset + 2, true);

        if (this._lastCrankRevs !== null) {
            const dRevs = (crankRevs - this._lastCrankRevs) & 0xFFFF;
            const dTime = (crankTime - this._lastCrankTime) & 0xFFFF;
            if (dRevs > 0 && dTime > 0) {
                // Actual new crank revolution — update cadence and optionally speed
                const s         = dTime / TIME_RESOLUTION;
                this.cadenceRpm = (dRevs / s) * 60;
                if (deriveSpeed) {
                    const wheelRps  = (this.cadenceRpm / 60) * GEAR_RATIO;
                    this.speedMs    = wheelRps * WHEEL_CIRCUMFERENCE;
                    this.distanceM += this.speedMs * s;
                }
            }
            // Frozen packet: keep last cadence/speed.
        }
        this._lastCrankRevs = crankRevs;
        this._lastCrankTime = crankTime;
    }

    _snapshot() {
        return {
            speed_ms:    Math.round(this.speedMs    * 1000) / 1000,
            speed_kmh:   Math.round(this.speedMs    * 3.6  * 100) / 100,
            cadence_rpm: Math.round(this.cadenceRpm * 10)  / 10,
            distance_m:  Math.round(this.distanceM  * 10)  / 10,
            distance_km: Math.round(this.distanceM  / 1000 * 1000) / 1000,
        };
    }

    reset() {
        this._lastWheelRevs = this._lastWheelTime = null;
        this._lastCrankRevs = this._lastCrankTime = null;
        this.distanceM = this.speedMs = this.cadenceRpm = 0;
    }
}

// ── UI refs ──────────────────────────────────────────────────────────────────
const bleDot      = document.getElementById('bleDot');
const bleStatus   = document.getElementById('bleStatus');
const btnConnect  = document.getElementById('btnConnect');
const btnDisc     = document.getElementById('btnDisconnect');
const wsDot       = document.getElementById('wsDot');
const wsStatusEl  = document.getElementById('wsStatus');
const metSpeed    = document.getElementById('metSpeed');
const metCadence  = document.getElementById('metCadence');
const metDistance = document.getElementById('metDistance');

// ── State ────────────────────────────────────────────────────────────────────
const metrics = new CSCMetrics();
let   device             = null;
let   ws                 = null;
let   sensorActive       = false;
let   lastNotificationMs = 0;

// ── Web Bluetooth availability check ────────────────────────────────────────
if (!navigator.bluetooth) {
    document.getElementById('noBle').style.display = 'block';
    btnConnect.disabled = true;
}

// ── WebSocket to backend ─────────────────────────────────────────────────────
function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws`);

    ws.onopen = () => {
        wsDot.className       = 'ws-dot ok';
        wsStatusEl.textContent = 'Backend connected';
    };
    ws.onclose = () => {
        wsDot.className       = 'ws-dot err';
        wsStatusEl.textContent = 'Backend disconnected — retrying…';
        setTimeout(connectWS, 3000);
    };
    ws.onerror = () => ws.close();
}

function sendToBackend(metricsData, active) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'sensor_metrics',
            active,
            ...metricsData,
        }));
    }
}

// ── BLE helpers ──────────────────────────────────────────────────────────────
function setBleState(state, text) {
    bleDot.className      = `ble-dot ${state}`;
    bleStatus.textContent = text;
}

async function connect() {
    try {
        setBleState('connecting', 'Scanning…');
        btnConnect.disabled = true;

        device = await navigator.bluetooth.requestDevice({
            filters: [{ services: [CSC_SERVICE] }],
        });

        device.addEventListener('gattserverdisconnected', onDisconnected);
        setBleState('connecting', 'Connecting…');

        const server  = await device.gatt.connect();
        const service = await server.getPrimaryService(CSC_SERVICE);
        const char    = await service.getCharacteristic(CSC_MEASUREMENT);

        metrics.reset();
        await char.startNotifications();
        char.addEventListener('characteristicvaluechanged', onCSC);

        setBleState('connected', `Connected — ${device.name || device.id}`);
        btnConnect.disabled = true;
        btnDisc.disabled    = false;

    } catch (err) {
        console.error(err);
        setBleState('disconnected', `Failed: ${err.message}`);
        btnConnect.disabled = false;
    }
}

function onCSC(event) {
    const data = metrics.update(event.target.value);
    lastNotificationMs = Date.now();
    sensorActive = true;
    updateUI(data);
}

// ── 1-second send interval ───────────────────────────────────────────────────
// Distance-based stop detection: only zero out after 3 consecutive ticks
// with no distance change (~3 s). A single frozen tick can happen at low
// speeds (slow wheel revolution > 1 s) and shouldn't count as stopped.
let _lastTickDistance = -1;
let _frozenTicks      = 0;
const FROZEN_THRESHOLD = 5;

setInterval(() => {
    if (device && device.gatt.connected) {
        if (metrics.distanceM === _lastTickDistance) {
            _frozenTicks++;
            if (_frozenTicks >= FROZEN_THRESHOLD) {
                metrics.speedMs    = 0;
                metrics.cadenceRpm = 0;
                sensorActive       = false;
            }
        } else {
            _frozenTicks = 0;
        }
        _lastTickDistance = metrics.distanceM;
        const snap = metrics._snapshot();
        sendToBackend(snap, sensorActive);
        updateUI(snap);
    }
}, 1000);

function updateUI(data) {
    metSpeed.textContent    = data.speed_kmh.toFixed(1);
    metCadence.textContent  = Math.round(data.cadence_rpm);
    metDistance.textContent = data.distance_km.toFixed(2);
}

function onDisconnected() {
    setBleState('disconnected', 'Disconnected');
    btnConnect.disabled = false;
    btnDisc.disabled    = true;
    sensorActive        = false;
    clearTimeout(stopTimer);
    sendToBackend({ speed_ms: 0, speed_kmh: 0, cadence_rpm: 0, distance_m: 0, distance_km: 0 }, false);
}

async function disconnect() {
    if (device && device.gatt.connected) {
        await device.gatt.disconnect();
    }
}

// ── Event listeners ──────────────────────────────────────────────────────────
btnConnect.addEventListener('click', connect);
btnDisc.addEventListener('click', disconnect);

// ── Boot ─────────────────────────────────────────────────────────────────────
connectWS();
