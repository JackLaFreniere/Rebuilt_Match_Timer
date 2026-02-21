// =============================================================================
//  FRC Match Timer - Client Script
//  Receives match data via a one-way WebSocket, computes game phases and hub
//  alternation locally, and renders a smooth countdown using requestAnimationFrame.
// =============================================================================

// -- Configuration ------------------------------------------------------------

const WS_URL       = "ws://127.0.0.1:8765";
const RECONNECT_MS = 1000;

// FRC 2025 match timing (seconds)
const AUTO_DURATION     = 20;
const TELEOP_DURATION   = 140;  // includes endgame
const TELEOP_TRANSITION = 10;   // both-hubs-on period at start of teleop
const HUB_PERIOD        = 25;   // each alternating hub window
const ENDGAME_START     = 30;   // matchTime <= 30 triggers endgame
const ALTERNATING_END   = 130;  // matchTime > 130 is teleop transition

const MATCH_TYPES = { 0: "Practice", 1: "Qual", 2: "Qual", 3: "Elim" };

// -- DOM References -----------------------------------------------------------

const eventNameEl        = document.getElementById("event-name");
const matchInfoEl        = document.getElementById("match-info");
const wsStatusEl         = document.getElementById("ws-status");
const dsStatusEl         = document.getElementById("ds-status");
const currentPhaseEl     = document.getElementById("current-phase");
const globalTimerEl      = document.getElementById("global-timer");
const phaseTimerEl       = document.getElementById("phase-timer");
const nextPhaseEl        = document.getElementById("next-phase");
const hubFillEl          = document.getElementById("hub-fill");
const hubGrayEl          = document.getElementById("hub-gray");
const nextHubIndicatorEl = document.getElementById("next-hub-indicator");
const gsmValueEl         = document.getElementById("gsm-value");
const gsmRedBtnEl        = document.getElementById("gsm-red-btn");
const gsmBlueBtnEl       = document.getElementById("gsm-blue-btn");
const gsmClearBtnEl      = document.getElementById("gsm-clear-btn");
const bodyEl             = document.body;

// -- State --------------------------------------------------------------------

let ws             = null;
let reconnectTimer = null;

// Tracks match progression and GSM across FMS updates
const gameState = {
    sawAuto:         false,
    sawTeleop:       false,
    gsmLocked:       "",      // value locked from FMS GameSpecificMessage
    gsmOverride:     null,    // manual operator override ("r" | "b" | null)
    _loggedFallback: false    // prevents alliance-fallback warning spam
};

// Interpolation anchors for smooth countdown between integer FMS ticks
let lastRawData      = null;
let lastReceiveTime  = 0;
let lastRawMatchTime = null;

// -- Formatting ---------------------------------------------------------------

/** Format seconds as "M:SS". Clamps negatives to 0, rounds up. */
function formatTime(seconds) {
    seconds = Math.max(0, Math.ceil(seconds));
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/** Like formatTime but omits the "0:" prefix when under a minute. */
function formatPhaseTime(seconds) {
    seconds = Math.max(0, Math.ceil(seconds));
    if (seconds < 60) return seconds.toString();
    return formatTime(seconds);
}

// -- GSM Override -------------------------------------------------------------

/** Set or clear the local GSM override (bypasses FMS GameSpecificMessage). */
function setGSMOverride(value) {
    if (value === 'r' || value === 'b') {
        gameState.gsmOverride = value;
        console.log(`[GSM] Override set: ${value === 'b' ? 'Blue' : 'Red'} off first`);
    } else {
        gameState.gsmOverride = null;
        console.log('[GSM] Override cleared');
    }
    renderInterpolated();
}

gsmRedBtnEl.addEventListener('click',   () => setGSMOverride('r'));
gsmBlueBtnEl.addEventListener('click',  () => setGSMOverride('b'));
gsmClearBtnEl.addEventListener('click', () => setGSMOverride(null));

// -- Game Logic ---------------------------------------------------------------

/**
 * Determine the current match phase and hub on/off states from raw FMS data.
 *
 * Phase flow: disconnected -> pre_match -> auto -> transition -> teleop -> endgame -> match_end
 *
 * Hub alternation during teleop (matchTime 130 to 30):
 *   GSM "b" = blue turns off first, "r" = red turns off first.
 *   Priority: manual override > locked FMS value > alliance-color fallback.
 */
function computePhaseAndHubs(rawData) {
    const dsAttached = rawData.DSAttatched || false;
    const enabled    = rawData.Enabled || false;
    const autonomous = rawData.Autonomous || false;
    const matchTime  = rawData.MatchTime || 0;
    const gsm        = rawData.GameSpecificMessage || "";

    // Lock GSM from FMS once received
    if (gsm === "b" || gsm === "r") {
        if (gameState.gsmLocked !== gsm) {
            console.log(`[GSM] FMS value: ${gsm === 'b' ? 'Blue' : 'Red'} off first`);
        }
        gameState.gsmLocked = gsm;
    }

    let phase;
    let blueHubActive = false;
    let redHubActive  = false;

    // Phase detection
    if (!dsAttached) {
        phase = "disconnected";
        gameState.sawAuto         = false;
        gameState.sawTeleop       = false;
        gameState.gsmLocked       = "";
        gameState._loggedFallback = false;
    } else if (!enabled) {
        if (gameState.sawTeleop)    phase = "match_end";
        else if (gameState.sawAuto) phase = "transition";
        else { phase = "pre_match"; gameState.gsmLocked = ""; }
    } else if (autonomous) {
        phase = "auto";
        gameState.sawAuto = true;
    } else {
        // Only flag sawTeleop once matchTime confirms the switch
        // (avoids race when Autonomous flips before Enabled during transition)
        if (matchTime > 1) gameState.sawTeleop = true;
        phase = matchTime <= ENDGAME_START ? "endgame" : "teleop";
    }

    // Hub states
    if (phase === "auto" || phase === "transition") {
        blueHubActive = true;
        redHubActive  = true;
    } else if (phase === "teleop" || phase === "endgame") {
        if (matchTime > ALTERNATING_END) {
            // First 10s of teleop - both hubs on
            blueHubActive = true;
            redHubActive  = true;
        } else if (matchTime > ENDGAME_START) {
            // Alternating 25s windows
            const elapsed = ALTERNATING_END - matchTime;
            const period  = Math.floor(elapsed / HUB_PERIOD);

            // Resolve which alliance turns off first
            let blueOffFirst;
            if (gameState.gsmOverride)    blueOffFirst = (gameState.gsmOverride === "b");
            else if (gameState.gsmLocked) blueOffFirst = (gameState.gsmLocked === "b");
            else {
                const isRedAlliance = rawData.isRedAlliance !== false;
                blueOffFirst = !isRedAlliance;
                if (!gameState._loggedFallback) {
                    console.log(`[GSM] No FMS value, falling back to alliance color (${blueOffFirst ? 'blue' : 'red'} off first)`);
                    gameState._loggedFallback = true;
                }
            }

            blueHubActive = (period % 2 === 0) ? !blueOffFirst : blueOffFirst;
            redHubActive  = (period % 2 === 0) ? blueOffFirst  : !blueOffFirst;
        } else {
            // Endgame - both hubs on
            blueHubActive = true;
            redHubActive  = true;
        }
    }

    return {
        ...rawData,
        phase,
        blueHubActive,
        redHubActive,
        GameSpecificMessage: gameState.gsmOverride || gameState.gsmLocked,
        GSMOverride: gameState.gsmOverride
    };
}

// -- Phase Info ---------------------------------------------------------------

/** Map phase + matchTime into display labels, countdowns, and durations. */
function getPhaseInfo(phase, matchTime, blueOn, redOn, gsm) {
    const info = { name: "", timeRemaining: 0, nextPhase: "", duration: 1 };

    switch (phase) {
        case "disconnected":
            info.name = "NOT CONNECTED";
            break;

        case "pre_match":
            info.name      = "READY";
            info.nextPhase = "Waiting for Auto...";
            break;

        case "auto":
            info.name          = "AUTONOMOUS";
            info.timeRemaining = matchTime;
            info.duration      = AUTO_DURATION;
            info.nextPhase     = "Next: Transition";
            break;

        case "transition":
            // 3s disabled gap - keep showing "AUTONOMOUS" at 0
            info.name = "AUTONOMOUS";
            break;

        case "teleop":
        case "endgame":
            if (matchTime > ALTERNATING_END) {
                info.name          = "TRANSITION";
                info.timeRemaining = matchTime - ALTERNATING_END;
                info.duration      = TELEOP_TRANSITION;
                info.nextPhase     = gsm === "b" ? "Next: Red Hub" : "Next: Blue Hub";
            } else if (matchTime > ENDGAME_START) {
                const elapsed    = ALTERNATING_END - matchTime;
                const period     = Math.floor(elapsed / HUB_PERIOD);
                const periodTime = elapsed % HUB_PERIOD;
                info.timeRemaining = HUB_PERIOD - periodTime;
                info.duration      = HUB_PERIOD;

                if (blueOn && !redOn) {
                    info.name      = "BLUE HUB";
                    info.nextPhase = "Next: Red Hub";
                } else if (redOn && !blueOn) {
                    info.name      = "RED HUB";
                    info.nextPhase = period === 3 ? "Next: Endgame" : "Next: Blue Hub";
                } else {
                    info.name = "TELEOP";
                }
            } else {
                info.name          = "ENDGAME";
                info.timeRemaining = matchTime;
                info.duration      = ENDGAME_START;
                info.nextPhase     = "Match ending soon!";
            }
            break;

        case "match_end":
            info.name = "MATCH OVER";
            break;
    }

    return info;
}

// -- Display ------------------------------------------------------------------

function updateDisplay(rawData) {
    const data = computePhaseAndHubs(rawData);

    // Info bar
    eventNameEl.textContent = data.EventName || "---";
    const matchType = MATCH_TYPES[data.MatchType] || "Match";
    matchInfoEl.textContent = data.MatchNumber ? `${matchType} ${data.MatchNumber}` : "---";

    updateGSMDisplay(data);

    // DS status
    dsStatusEl.classList.toggle("connected",    !!data.DSAttatched);
    dsStatusEl.classList.toggle("disconnected", !data.DSAttatched);

    // Alliance border
    bodyEl.classList.remove("red-alliance", "blue-alliance", "disconnected", "match-ended");
    if      (data.phase === "disconnected") bodyEl.classList.add("disconnected");
    else if (data.phase === "match_end")    bodyEl.classList.add("match-ended");
    else if (data.isRedAlliance)            bodyEl.classList.add("red-alliance");
    else                                    bodyEl.classList.add("blue-alliance");

    const phaseInfo = getPhaseInfo(
        data.phase, data.MatchTime || 0,
        data.blueHubActive, data.redHubActive,
        data.GameSpecificMessage || ""
    );
    currentPhaseEl.textContent = phaseInfo.name;
    nextPhaseEl.textContent    = phaseInfo.nextPhase;

    // Global timer: total match = 20s auto + 140s teleop (transition excluded)
    if (data.phase === "disconnected" || data.phase === "pre_match") {
        globalTimerEl.textContent = "--:--";
    } else if (data.phase === "match_end") {
        globalTimerEl.textContent = "0:00";
    } else if (data.phase === "auto") {
        globalTimerEl.textContent = formatTime((data.MatchTime || 0) + TELEOP_DURATION);
    } else if (data.phase === "transition") {
        globalTimerEl.textContent = "2:20";
    } else {
        globalTimerEl.textContent = formatTime(data.MatchTime || 0);
    }

    // Phase timer
    if (data.phase === "disconnected" || data.phase === "pre_match") {
        phaseTimerEl.textContent = "--";
    } else if (data.phase === "match_end") {
        phaseTimerEl.textContent = "";
    } else {
        phaseTimerEl.textContent = formatPhaseTime(phaseInfo.timeRemaining);
    }

    updateHubDisplay(data);
}

function updateGSMDisplay(data) {
    const override  = data.GSMOverride;
    const effective = override || gameState.gsmLocked;

    if      (effective === 'r') { gsmValueEl.textContent = 'R';   gsmValueEl.className = 'gsm-value red'; }
    else if (effective === 'b') { gsmValueEl.textContent = 'B';   gsmValueEl.className = 'gsm-value blue'; }
    else                        { gsmValueEl.textContent = '---'; gsmValueEl.className = 'gsm-value'; }

    if (override) gsmValueEl.classList.add('overridden');

    gsmRedBtnEl.classList.toggle('active',  override === 'r');
    gsmBlueBtnEl.classList.toggle('active', override === 'b');
}

function updateHubDisplay(data) {
    const { phase, blueHubActive: blueOn, redHubActive: redOn,
            MatchTime: matchTime = 0, GameSpecificMessage: gsm = "" } = data;

    hubFillEl.className          = "";
    nextHubIndicatorEl.className = "";

    // Static states
    if (phase === "disconnected") {
        hubFillEl.style.width = "100%";
        hubGrayEl.style.width = "100%";
        return;
    }
    if (phase === "pre_match") {
        hubFillEl.style.width = "100%";
        hubGrayEl.style.width = "0%";
        hubFillEl.classList.add("waiting");
        return;
    }
    if (phase === "match_end") {
        hubFillEl.style.width = "100%";
        hubGrayEl.style.width = "100%";
        hubFillEl.classList.add("match-end");
        return;
    }

    // Active match: gray sweeps left to right as time elapses
    hubFillEl.style.width  = "100%";
    let grayProgress       = 0;
    let showNextIndicator  = false;
    let nextIsBlue         = false;

    if (phase === "auto") {
        grayProgress = ((AUTO_DURATION - matchTime) / AUTO_DURATION) * 100;
        hubFillEl.classList.add("both-active");

    } else if (phase === "transition") {
        grayProgress = 100;
        hubFillEl.classList.add("both-active");

    } else if (phase === "teleop" || phase === "endgame") {
        if (matchTime > ALTERNATING_END) {
            // Teleop transition: both hubs on, preview next hub
            grayProgress = ((TELEOP_DURATION - matchTime) / TELEOP_TRANSITION) * 100;
            hubFillEl.classList.add("transition");
            showNextIndicator = true;
            nextIsBlue = (gsm !== "b");

        } else if (matchTime > ENDGAME_START) {
            // Alternating hub periods
            const elapsed    = ALTERNATING_END - matchTime;
            const period     = Math.floor(elapsed / HUB_PERIOD);
            const periodTime = elapsed % HUB_PERIOD;
            grayProgress = (periodTime / HUB_PERIOD) * 100;

            if (blueOn && !redOn) {
                hubFillEl.classList.add("blue-active");
                showNextIndicator = true;
                if (period === 3) nextHubIndicatorEl.classList.add("green-next");
                else              nextIsBlue = false;
            } else if (redOn && !blueOn) {
                hubFillEl.classList.add("red-active");
                showNextIndicator = true;
                if (period === 3) nextHubIndicatorEl.classList.add("green-next");
                else              nextIsBlue = true;
            } else {
                hubFillEl.classList.add("both-active");
            }

        } else {
            // Endgame: both hubs
            grayProgress = ((ENDGAME_START - matchTime) / ENDGAME_START) * 100;
            hubFillEl.classList.add("both-active", "endgame-pulse");
        }
    }

    hubGrayEl.style.width = `${grayProgress}%`;

    if (showNextIndicator) {
        nextHubIndicatorEl.classList.add("show");
        if (!nextHubIndicatorEl.classList.contains("green-next")) {
            nextHubIndicatorEl.classList.add(nextIsBlue ? "blue-next" : "red-next");
        }
    }
}

// -- Interpolation ------------------------------------------------------------

/**
 * Smooth countdown: subtract wall-clock time elapsed since the last integer FMS
 * tick, giving ~60fps rendering between whole-second server updates.
 */
function renderInterpolated() {
    if (!lastRawData) return;

    const data  = { ...lastRawData };
    const rawMT = data.MatchTime || 0;

    if (data.Enabled && rawMT > 0) {
        const elapsed  = (performance.now() - lastReceiveTime) / 1000;
        data.MatchTime = Math.max(0, rawMT - elapsed);
    }

    updateDisplay(data);
}

function animationLoop() {
    renderInterpolated();
    requestAnimationFrame(animationLoop);
}

// -- WebSocket ----------------------------------------------------------------

function connectWebSocket() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }

    // Tear down existing socket
    if (ws) {
        ws.onopen = ws.onmessage = ws.onclose = ws.onerror = null;
        try { ws.close(); } catch (_) {}
        ws = null;
    }

    try {
        ws = new WebSocket(WS_URL);
    } catch (_) {
        console.log("WebSocket creation failed, retrying...");
        scheduleReconnect();
        return;
    }

    ws.onopen = () => {
        wsStatusEl.classList.remove("disconnected");
        wsStatusEl.classList.add("connected");
        console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
        const data  = JSON.parse(event.data);
        const now   = performance.now();
        const rawMT = data.MatchTime || 0;

        if (rawMT !== lastRawMatchTime) {
            lastRawMatchTime = rawMT;
            lastReceiveTime  = now;
        }

        lastRawData = data;
        renderInterpolated();
    };

    ws.onclose = () => {
        wsStatusEl.classList.remove("connected");
        wsStatusEl.classList.add("disconnected");
        console.log("WebSocket disconnected, reconnecting...");
        updateDisplay({ phase: "disconnected", DSAttatched: false });
        scheduleReconnect();
    };

    ws.onerror = () => {};  // onclose fires after - reconnect handled there
}

function scheduleReconnect() {
    if (!reconnectTimer) {
        reconnectTimer = setTimeout(connectWebSocket, RECONNECT_MS);
    }
}

// -- Init ---------------------------------------------------------------------

requestAnimationFrame(animationLoop);
connectWebSocket();