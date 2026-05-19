// ── Constants ────────────────────────────────────────────────────────────────
const CSC_SERVICE     = '00001816-0000-1000-8000-00805f9b34fb';
const CSC_MEASUREMENT = '00002a5b-0000-1000-8000-00805f9b34fb';
const SC_CP           = '00002a55-0000-1000-8000-00805f9b34fb';

// XOSS proprietary service / characteristic for mode switching
const NUS_SERVICE     = '6e400001-b5a3-f393-e0a9-e50e24dcca9e';
const NUS_UNK         = '6e400004-b5a3-f393-e0a9-e50e24dcca9e';

const WHEEL_CIRCUMFERENCE = 2.1;
const GEAR_RATIO          = 2.8;
const TIME_RESOLUTION     = 1024;

// ── CSCMetrics ───────────────────────────────────────────────────────────────
class CSCMetrics {
    constructor() {
        this._lastWheelRevs = null;
        this._lastWheelTime = null;
        this._lastCrankRevs = null;
        this._lastCrankTime = null;
        this.distanceM  = 0;
        this.speedMs    = 0;
        this.cadenceRpm = 0;
    }

    update(dataView) {
        const flags    = dataView.getUint8(0);
        let   offset   = 1;
        const hasWheel = !!(flags & 0x01);
        const hasCrank = !!(flags & 0x02);

        if (hasWheel && dataView.byteLength >= offset + 6)
            offset = this._parseWheel(dataView, offset);

        if (hasCrank && dataView.byteLength >= offset + 4)
            this._parseCrank(dataView, offset, !hasWheel);

        return { flags, hasWheel, hasCrank, ...this._snapshot() };
    }

    _parseWheel(dv, offset) {
        const wheelRevs = dv.getUint32(offset,     true);
        const wheelTime = dv.getUint16(offset + 4, true);

        if (this._lastWheelRevs !== null) {
            const dRevs = (wheelRevs - this._lastWheelRevs) >>> 0;
            const dTime = (wheelTime - this._lastWheelTime) & 0xFFFF;
            if (dRevs > 0 && dTime > 0) {
                const s    = dTime / TIME_RESOLUTION;
                const dist = dRevs * WHEEL_CIRCUMFERENCE;
                this.distanceM += dist;
                this.speedMs    = dist / s;
            }
            // Frozen packet: hold last speed — interval handles zeroing
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
                const s         = dTime / TIME_RESOLUTION;
                this.cadenceRpm = (dRevs / s) * 60;
                if (deriveSpeed) {
                    const wheelRps  = (this.cadenceRpm / 60) * GEAR_RATIO;
                    this.speedMs    = wheelRps * WHEEL_CIRCUMFERENCE;
                    this.distanceM += this.speedMs * s;
                }
            }
            // Frozen packet: hold last values
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
const bleDot     = document.getElementById('bleDot');
const bleStatus  = document.getElementById('bleStatus');
const btnConnect = document.getElementById('btnConnect');
const btnSwitch  = document.getElementById('btnSwitch');

// ── State ────────────────────────────────────────────────────────────────────
const metrics = new CSCMetrics();
let   device              = null;
let   ws                  = null;
let   sensorActive        = false;
let   lastNotificationMs  = 0;
let   currentMode         = null;  // 'speed' | 'cadence' | 'combined'
let   isSwitching         = false;

// ── Helpers ──────────────────────────────────────────────────────────────────
function makeCmd(v) {
    return new Uint8Array([0x30, v, 0x30 ^ v]);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Web Bluetooth check ──────────────────────────────────────────────────────
if (!navigator.bluetooth) {
    bleStatus.textContent = 'BLE unavailable';
    btnConnect.disabled   = true;
}

// ── WebSocket ────────────────────────────────────────────────────────────────
function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws`);
    ws.onclose = () => setTimeout(connectWS, 3000);
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

// ── BLE state ────────────────────────────────────────────────────────────────
function setBleState(state, text) {
    bleDot.className      = `ble-dot ${state}`;
    bleStatus.textContent = text;
    btnConnect.classList.toggle('hidden', state === 'connected' || isSwitching);
}

function updateSwitchButton() {
    if (!currentMode || currentMode === 'combined' || isSwitching) {
        btnSwitch.classList.add('hidden');
        return;
    }
    const target = currentMode === 'speed' ? 'CAD' : 'SPD';
    btnSwitch.textContent = `⇄ ${target}`;
    btnSwitch.classList.remove('hidden');
    btnSwitch.disabled = false;
}

// ── BLE connect ──────────────────────────────────────────────────────────────
async function connect() {
    try {
        setBleState('connecting', 'Scanning…');
        btnConnect.disabled = true;

        device = await navigator.bluetooth.requestDevice({
            filters:          [{ services: [CSC_SERVICE] }],
            optionalServices: [NUS_SERVICE],
        });

        device.addEventListener('gattserverdisconnected', onDisconnected);
        setBleState('connecting', 'Connecting…');

        const server  = await device.gatt.connect();
        const service = await server.getPrimaryService(CSC_SERVICE);
        const char    = await service.getCharacteristic(CSC_MEASUREMENT);

        metrics.reset();
        currentMode = null;
        await char.startNotifications();
        char.addEventListener('characteristicvaluechanged', onCSC);

        setBleState('connected', device.name || 'Connected');

    } catch (err) {
        console.error('[SensorFrame]', err);
        setBleState('disconnected', 'Failed — retry?');
        btnConnect.disabled = false;
    }
}

function onCSC(event) {
    const result = metrics.update(event.target.value);
    lastNotificationMs = Date.now();
    sensorActive = true;

    // Detect sensor mode from CSC flags on first notification
    if (currentMode === null) {
        if (result.hasWheel && !result.hasCrank) currentMode = 'speed';
        else if (result.hasCrank && !result.hasWheel) currentMode = 'cadence';
        else if (result.hasWheel && result.hasCrank)  currentMode = 'combined';
        updateSwitchButton();
    }
}

function onDisconnected() {
    if (isSwitching) return;  // switch handler manages its own state
    setBleState('disconnected', 'Disconnected');
    btnConnect.disabled = false;
    btnSwitch.classList.add('hidden');
    sensorActive        = false;
    currentMode         = null;
    sendToBackend({ speed_ms: 0, speed_kmh: 0, cadence_rpm: 0, distance_m: 0, distance_km: 0 }, false);
}

// ── 1-second send interval ───────────────────────────────────────────────────
let _lastTickDistance = -1;
let _frozenTicks      = 0;
const FROZEN_THRESHOLD = 5;

setInterval(() => {
    if (device && device.gatt.connected && !isSwitching) {
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
        sendToBackend(metrics._snapshot(), sensorActive);
    }
}, 1000);

// ── XOSS mode switch ─────────────────────────────────────────────────────────
async function switchMode() {
    if (!device || !currentMode || currentMode === 'combined' || isSwitching) return;

    const targetMode = currentMode === 'speed' ? 'cadence' : 'speed';
    isSwitching = true;
    btnSwitch.classList.add('hidden');
    btnConnect.classList.add('hidden');

    setBleState('connecting', `Switching to ${targetMode}…`);

    try {
        // Re-connect if needed (after earlier CSC session)
        if (!device.gatt.connected) {
            setBleState('connecting', 'Reconnecting for switch…');
            await device.gatt.connect();
        }

        const server = device.gatt;

        // Stop CSC notifications before repurposing the connection
        try {
            const cscSvc  = await server.getPrimaryService(CSC_SERVICE);
            const cscChar = await cscSvc.getCharacteristic(CSC_MEASUREMENT);
            await cscChar.stopNotifications();
        } catch (_) {}

        // Wait for sensor reboot (disconnect) during switch
        const rebootPromise = new Promise(resolve => {
            device.addEventListener('gattserverdisconnected', resolve, { once: true });
        });

        if (targetMode === 'cadence') {
            const nusSvc  = await server.getPrimaryService(NUS_SERVICE);
            const nusChar = await nusSvc.getCharacteristic(NUS_UNK);
            await xossToCadence(nusChar, setBleState);
        } else {
            const nusSvc  = await server.getPrimaryService(NUS_SERVICE);
            const nusChar = await nusSvc.getCharacteristic(NUS_UNK);
            const cscSvc  = await server.getPrimaryService(CSC_SERVICE);
            const scCp    = await cscSvc.getCharacteristic(SC_CP);
            await xossToSpeed(nusChar, scCp, setBleState);
        }

        setBleState('connecting', 'Waiting for reboot…');
        await Promise.race([
            rebootPromise,
            sleep(15000),
        ]);

        setBleState('disconnected', `→ ${targetMode} mode — reconnect`);
        currentMode = targetMode;

    } catch (err) {
        console.error('[SensorFrame switch]', err);
        setBleState('disconnected', `Switch failed — reconnect`);
    } finally {
        isSwitching         = false;
        sensorActive        = false;
        btnConnect.disabled = false;
        btnConnect.classList.remove('hidden');
    }
}

async function xossToCadence(nusChar, progress) {
    const ticks = [];
    const onTick = (event) => {
        const data = new Uint8Array(event.target.value.buffer);
        if (data.length >= 3 && data[0] === 0x31 && data[2] === (0x31 ^ data[1]))
            ticks.push(data[1]);
    };
    try {
        nusChar.addEventListener('characteristicvaluechanged', onTick);
        await nusChar.startNotifications();
    } catch (_) {}

    await nusChar.writeValueWithoutResponse(makeCmd(0x01));
    await sleep(500);

    const counter = ticks.length > 0 ? ticks[ticks.length - 1] : 0x01;
    const jump    = (0x24 - counter) & 0xFF;
    progress('connecting', `Jumping +0x${jump.toString(16).toUpperCase().padStart(2, '0')}…`);
    await nusChar.writeValueWithoutResponse(makeCmd(jump));
}

async function xossToSpeed(nusChar, scCp, progress) {
    // Set sensor location to Front Wheel (0x04) first
    await xossSetLocation(scCp, 0x04);

    try { await nusChar.startNotifications(); } catch (_) {}

    for (let val = 0; val < 0x100; val++) {
        if (!device || !device.gatt.connected) break;
        try {
            await nusChar.writeValueWithoutResponse(makeCmd(val));
        } catch (_) { break; }
        if (val % 32 === 0)
            progress('connecting', `Sweep 0x${val.toString(16).padStart(2, '0')}/0xFF…`);
        await sleep(80);
    }
}

async function xossSetLocation(scCp, loc) {
    return new Promise(async (resolve) => {
        const onResp = () => resolve();
        const timer  = setTimeout(resolve, 3000);
        try {
            scCp.addEventListener('characteristicvaluechanged', onResp, { once: true });
            await scCp.startNotifications();
            await scCp.writeValueWithResponse(new Uint8Array([0x03, loc]));
        } catch (_) {
            clearTimeout(timer);
            resolve();
        }
    });
}

// ── Auto-reconnect on load ───────────────────────────────────────────────────
// Chrome remembers previously-paired BLE devices. On reload, try to silently
// reconnect without showing the picker dialog.
async function tryAutoConnect() {
    if (!navigator.bluetooth?.getDevices) return;
    try {
        const devices = await navigator.bluetooth.getDevices();
        if (devices.length === 0) return;

        // Use the first previously-paired device (most recently used)
        device = devices[0];
        device.addEventListener('gattserverdisconnected', onDisconnected);
        setBleState('connecting', `Reconnecting ${device.name || '…'}…`);
        btnConnect.classList.add('hidden');

        const server  = await device.gatt.connect();
        const service = await server.getPrimaryService(CSC_SERVICE);
        const char    = await service.getCharacteristic(CSC_MEASUREMENT);

        metrics.reset();
        currentMode = null;
        await char.startNotifications();
        char.addEventListener('characteristicvaluechanged', onCSC);

        setBleState('connected', device.name || 'Connected');
    } catch (_) {
        // Auto-connect failed silently — user can connect manually
        device = null;
        setBleState('disconnected', 'Sensor');
        btnConnect.classList.remove('hidden');
        btnConnect.disabled = false;
    }
}

// ── Events & boot ────────────────────────────────────────────────────────────
btnConnect.addEventListener('click', connect);
btnSwitch.addEventListener('click', switchMode);
connectWS();
tryAutoConnect();
