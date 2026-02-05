const ws = new WebSocket("ws://127.0.0.1:8765");

// Elements
const eventNameEl = document.getElementById("event-name");
const matchInfoEl = document.getElementById("match-info");
const wsStatusEl = document.getElementById("ws-status");
const dsStatusEl = document.getElementById("ds-status");
const currentPhaseEl = document.getElementById("current-phase");
const globalTimerEl = document.getElementById("global-timer");
const phaseTimerEl = document.getElementById("phase-timer");
const nextPhaseEl = document.getElementById("next-phase");
const hubFillEl = document.getElementById("hub-fill");
const hubGrayEl = document.getElementById("hub-gray");
const nextHubIndicatorEl = document.getElementById("next-hub-indicator");
const bodyEl = document.body;

// Match type names
const matchTypes = {
    0: "Practice",
    1: "Qual",
    2: "Qual",
    3: "Elim"
};

// Phase durations for calculating phase time remaining
const PHASE_DURATIONS = {
    auto: 20,
    teleop_both: 10,
    teleop_alt: 25,
    endgame: 30
};

function formatTime(seconds) {
    if (seconds < 0) seconds = 0;
    if (seconds === 0) {
        // Handle exact zero case
        return "0:00";
    }
    seconds = Math.ceil(seconds);  // Round up to show current second
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatPhaseTime(seconds) {
    // For phase timer, just show seconds if under a minute
    if (seconds < 0) seconds = 0;
    seconds = Math.ceil(seconds);
    if (seconds < 60) {
        return seconds.toString();
    }
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function getPhaseInfo(phase, matchTime, blueOn, redOn, gsm) {
    // Returns { name, timeRemaining, nextPhase, duration }
    let info = { name: "", timeRemaining: 0, nextPhase: "", duration: 1 };
    
    if (phase === "disconnected") {
        info.name = "NOT CONNECTED";
        info.nextPhase = "";
    } else if (phase === "pre_match") {
        info.name = "READY";
        info.nextPhase = "Waiting for Auto...";
    } else if (phase === "auto") {
        info.name = "AUTONOMOUS";
        info.timeRemaining = matchTime;
        info.duration = 20;
        info.nextPhase = "Next: Transition";
    } else if (phase === "transition") {
        // 3 second disabled period - keep showing auto at 0
        info.name = "AUTONOMOUS";
        info.timeRemaining = 0;
        info.duration = 1;
        info.nextPhase = "";
    } else if (phase === "teleop" || phase === "endgame") {
        if (matchTime > 130) {
            // First 10 seconds - both hubs on, this is the "transition" period in teleop
            info.name = "TRANSITION";
            info.timeRemaining = matchTime - 130;
            info.duration = 10;
            // GSM "b" = blue off first = red on next, "r" = red off first = blue on next
            info.nextPhase = gsm === "b" ? "Next: Red Hub" : "Next: Blue Hub";
        } else if (matchTime > 30) {
            // Alternating periods
            const elapsed = 130 - matchTime;
            const period = Math.floor(elapsed / 25);
            const periodTime = elapsed % 25;
            info.timeRemaining = 25 - periodTime;
            info.duration = 25;
            
            if (blueOn && !redOn) {
                info.name = "BLUE HUB";
                info.nextPhase = "Next: Red Hub";
            } else if (redOn && !blueOn) {
                info.name = "RED HUB";
                info.nextPhase = period === 3 ? "Next: Endgame" : "Next: Blue Hub";
            } else {
                info.name = "TELEOP";
            }
        } else {
            // Endgame
            info.name = "ENDGAME";
            info.timeRemaining = matchTime;
            info.duration = 30;
            info.nextPhase = "Match ending soon!";
        }
    } else if (phase === "match_end") {
        info.name = "MATCH OVER";
        info.nextPhase = "";
    }
    
    return info;
}

function getPhaseTimeRemaining(phase, matchTime) {
    // Calculate time remaining in current phase segment
    if (phase === "auto") {
        return matchTime; // Auto counts down from 20
    } else if (phase === "transition") {
        return 3; // Fixed 3 second transition
    } else if (phase === "teleop" || phase === "endgame") {
        if (matchTime > 130) {
            // First 10 seconds of teleop
            return matchTime - 130;
        } else if (matchTime > 30) {
            // Alternating periods (each 25s)
            const elapsed = 130 - matchTime;
            const periodTime = elapsed % 25;
            return 25 - periodTime;
        } else {
            // Endgame
            return matchTime;
        }
    }
    return 0;
}

function updateDisplay(data) {
    // Update info bar
    eventNameEl.textContent = data.EventName || "---";
    
    const matchType = matchTypes[data.MatchType] || "Match";
    matchInfoEl.textContent = data.MatchNumber ? `${matchType} ${data.MatchNumber}` : "---";
    
    // DS status
    if (data.DSAttached) {
        dsStatusEl.classList.remove("disconnected");
        dsStatusEl.classList.add("connected");
    } else {
        dsStatusEl.classList.remove("connected");
        dsStatusEl.classList.add("disconnected");
    }
    
    // Alliance border
    bodyEl.classList.remove("red-alliance", "blue-alliance", "disconnected", "match-ended");
    if (data.phase === "disconnected") {
        bodyEl.classList.add("disconnected");
    } else if (data.phase === "match_end") {
        bodyEl.classList.add("match-ended");
    } else if (data.isRedAlliance) {
        bodyEl.classList.add("red-alliance");
    } else {
        bodyEl.classList.add("blue-alliance");
    }
    
    // Get phase info
    const phaseInfo = getPhaseInfo(
        data.phase, 
        data.MatchTime || 0, 
        data.blueHubActive, 
        data.redHubActive,
        data.GameSpecificMessage || ""
    );
    
    // Phase display
    currentPhaseEl.textContent = phaseInfo.name;
    nextPhaseEl.textContent = phaseInfo.nextPhase;
    
    // Global timer (total match time)
    // Total match = 20s auto + 140s teleop = 160s (2:40)
    // Transition is NOT counted - it's a disabled period
    if (data.phase === "disconnected" || data.phase === "pre_match") {
        globalTimerEl.textContent = "--:--";
    } else if (data.phase === "match_end") {
        globalTimerEl.textContent = "0:00";
    } else if (data.phase === "auto") {
        // During auto, show auto time + 140 for total
        globalTimerEl.textContent = formatTime((data.MatchTime || 0) + 140);
    } else if (data.phase === "transition") {
        // Transition doesn't count - show 2:20 (waiting for teleop)
        globalTimerEl.textContent = "2:20";
    } else {
        globalTimerEl.textContent = formatTime(data.MatchTime || 0);
    }
    
    // Phase timer (time in current phase)
    if (data.phase === "disconnected" || data.phase === "pre_match") {
        phaseTimerEl.textContent = "--";
    } else if (data.phase === "match_end") {
        phaseTimerEl.textContent = "";
    } else {
        phaseTimerEl.textContent = formatPhaseTime(phaseInfo.timeRemaining);
    }
    
    // Hub display
    updateHubDisplay(data, phaseInfo);
}

function updateHubDisplay(data, phaseInfo) {
    const phase = data.phase;
    const blueOn = data.blueHubActive;
    const redOn = data.redHubActive;
    const matchTime = data.MatchTime || 0;
    const gsm = data.GameSpecificMessage || "";
    
    // Clear classes
    hubFillEl.className = "";
    nextHubIndicatorEl.className = "";
    
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
    
    // Full screen is colored, gray sweeps from LEFT to RIGHT
    // Gray width = elapsed percentage, color shows on right
    hubFillEl.style.width = "100%";
    
    let grayProgress = 0;
    let showNextIndicator = false;
    let nextIsBlue = false;
    
    if (phase === "auto") {
        grayProgress = ((20 - matchTime) / 20) * 100;
        hubFillEl.classList.add("both-active");
    } else if (phase === "transition") {
        // Stay fully grayed during 3s disabled period
        grayProgress = 100;
        hubFillEl.classList.add("both-active");
    } else if (phase === "teleop" || phase === "endgame") {
        if (matchTime > 130) {
            // First 10 seconds - transition period, both hubs on
            // Show indicator for which hub is coming next
            grayProgress = ((140 - matchTime) / 10) * 100;
            hubFillEl.classList.add("transition");
            
            // GSM tells us which hub turns OFF first
            // So if "b" = blue off first = red is on next
            showNextIndicator = true;
            nextIsBlue = (gsm !== "b"); // If blue off first, red is next (so nextIsBlue = false)
        } else if (matchTime > 30) {
            // Alternating periods
            const elapsed = 130 - matchTime;
            const period = Math.floor(elapsed / 25);
            const periodTime = elapsed % 25;
            grayProgress = (periodTime / 25) * 100;
            
            if (blueOn && !redOn) {
                hubFillEl.classList.add("blue-active");
                showNextIndicator = true;
                if (period === 3) {
                    // Last period before endgame - show green
                    nextHubIndicatorEl.classList.add("green-next");
                } else {
                    nextIsBlue = false; // Red is next
                }
            } else if (redOn && !blueOn) {
                hubFillEl.classList.add("red-active");
                showNextIndicator = true;
                if (period === 3) {
                    // Last period before endgame - show green
                    nextHubIndicatorEl.classList.add("green-next");
                } else {
                    nextIsBlue = true; // Blue is next
                }
            } else {
                hubFillEl.classList.add("both-active");
            }
        } else {
            // Endgame - both on
            grayProgress = ((30 - matchTime) / 30) * 100;
            hubFillEl.classList.add("both-active", "endgame-pulse");
        }
    }
    
    hubGrayEl.style.width = `${grayProgress}%`;
    
    // Update next hub indicator
    if (showNextIndicator) {
        nextHubIndicatorEl.classList.add("show");
        // Only add blue/red if green wasn't already added (for endgame preview)
        if (!nextHubIndicatorEl.classList.contains("green-next")) {
            nextHubIndicatorEl.classList.add(nextIsBlue ? "blue-next" : "red-next");
        }
    }
}

// WebSocket handlers
ws.onopen = () => {
    wsStatusEl.classList.remove("disconnected");
    wsStatusEl.classList.add("connected");
    console.log("WebSocket connected");
};

ws.onmessage = (event) => {
    console.log("Received data:", event.data);
    const data = JSON.parse(event.data);
    updateDisplay(data);
};

ws.onclose = () => {
    wsStatusEl.classList.remove("connected");
    wsStatusEl.classList.add("disconnected");
    console.log("WebSocket disconnected");
    
    // Show disconnected state
    updateDisplay({
        phase: "disconnected",
        DSAttached: false
    });
};

ws.onerror = (error) => {
    console.log("WebSocket error:", error);
};