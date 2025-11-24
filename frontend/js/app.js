// API Base URL
const API_URL = window.location.origin + '/api';

// State
let currentScreen = 'selection';
let currentSession = null;
let characters = [];
let sessionStats = {
    punches: 0,
    totalForce: 0,
    maxForce: 0
};

// Elements
const screens = {
    selection: document.getElementById('screen-selection'),
    create: document.getElementById('screen-create'),
    workout: document.getElementById('screen-workout'),
    stats: document.getElementById('screen-stats')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadCharacters();
    setupEventListeners();
    updateIntensityDisplay();
});

// ===== Navigation =====

function showScreen(screenName) {
    Object.values(screens).forEach(screen => screen.classList.remove('active'));
    screens[screenName].classList.add('active');
    currentScreen = screenName;
}

// ===== Character Management =====

async function loadCharacters() {
    try {
        const response = await fetch(`${API_URL}/characters`);
        characters = await response.json();
        renderCharacterGrid();
    } catch (error) {
        console.error('Error loading characters:', error);
        alert('Failed to load characters');
    }
}

function renderCharacterGrid() {
    const grid = document.getElementById('character-grid');
    grid.innerHTML = '';

    if (characters.length === 0) {
        grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #888;">No characters yet. Create your first rival!</p>';
        return;
    }

    characters.forEach(char => {
        const card = document.createElement('div');
        card.className = 'character-card';
        card.innerHTML = `
            <div class="char-emoji">${getCharacterEmoji(char.relationship)}</div>
            <div class="char-name">${char.name}</div>
            <div class="char-relationship">${capitalizeFirst(char.relationship)}</div>
            <div class="char-stats">${char.total_sessions || 0} sessions</div>
        `;
        card.onclick = () => startWorkoutWithCharacter(char.id);
        grid.appendChild(card);
    });
}

function getCharacterEmoji(relationship) {
    const emojiMap = {
        boss: '💼',
        coworker: '🤝',
        rival: '⚔️',
        ex: '💔',
        trainer: '💪',
        fictional: '🎭',
        custom: '🎯'
    };
    return emojiMap[relationship] || '🥊';
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// ===== Character Creation =====

function setupEventListeners() {
    // Create character button
    document.getElementById('btn-create-character').onclick = () => {
        showScreen('create');
        loadVoices();  // Load voices when create screen is shown
    };

    // Cancel create
    document.getElementById('btn-cancel-create').onclick = () => {
        document.getElementById('form-create-character').reset();
        showScreen('selection');
    };

    // Intensity slider
    document.getElementById('char-intensity').oninput = updateIntensityDisplay;

    // Voice cloning modal
    document.getElementById('btn-clone-voice').onclick = () => {
        document.getElementById('voice-clone-modal').style.display = 'block';
    };

    document.getElementById('btn-cancel-clone').onclick = () => {
        document.getElementById('voice-clone-modal').style.display = 'none';
        // Reset form
        document.getElementById('clone-voice-name').value = '';
        document.getElementById('clone-voice-sample').value = '';
        document.getElementById('clone-consent-checkbox').checked = false;
        document.getElementById('clone-status').style.display = 'none';
    };

    document.getElementById('btn-submit-clone').onclick = cloneVoice;

    // Form submit
    document.getElementById('form-create-character').onsubmit = async (e) => {
        e.preventDefault();
        await createCharacter();
    };

    // End workout
    document.getElementById('btn-end-workout').onclick = endWorkout;

    // Simulate punch (for testing)
    document.getElementById('btn-simulate-punch').onclick = simulatePunch;

    // Back from stats
    document.getElementById('btn-back-stats').onclick = () => {
        showScreen('selection');
    };

    // Feedback mode change
    document.getElementById('feedback-mode').onchange = async (e) => {
        const mode = e.target.value;
        localStorage.setItem('feedbackMode', mode);
        console.log(`Feedback mode changed to: ${mode}`);

        // Update current session immediately if one is active
        if (currentSession && currentSession.session_id) {
            try {
                const response = await fetch(`${API_URL}/sessions/${currentSession.session_id}/feedback-mode`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ feedback_mode: mode })
                });

                if (response.ok) {
                    console.log(`✅ Feedback mode updated to ${mode} for current session`);
                    // Show brief notification
                    showModeChangeNotification(mode);
                } else {
                    console.error('Failed to update feedback mode');
                }
            } catch (error) {
                console.error('Error updating feedback mode:', error);
            }
        }
    };

    // Settings panel toggle
    document.getElementById('btn-toggle-settings').onclick = () => {
        const panel = document.getElementById('settings-panel');
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';

        // Load current settings when opening
        if (panel.style.display === 'block') {
            loadSensorSettings();
        }
    };

    // Save settings
    document.getElementById('btn-save-settings').onclick = saveSensorSettings;

    // Reset settings
    document.getElementById('btn-reset-settings').onclick = resetSensorSettings;

    // Debug panel toggle
    document.getElementById('btn-toggle-debug').onclick = () => {
        const panel = document.getElementById('debug-panel');
        const btn = document.getElementById('btn-toggle-debug');

        if (panel.style.display === 'none') {
            panel.style.display = 'block';
            btn.textContent = 'Hide Debug';
            startDebugPolling();
        } else {
            panel.style.display = 'none';
            btn.textContent = 'Show Debug';
            stopDebugPolling();
        }
    };
}

async function loadSensorSettings() {
    try {
        const response = await fetch(`${API_URL}/sensor/config`);
        if (response.ok) {
            const config = await response.json();
            document.getElementById('setting-hit-start').value = config.hit_start_g;
            document.getElementById('setting-hit-end').value = config.hit_end_g;
            document.getElementById('setting-end-samples').value = config.end_samples;
            document.getElementById('setting-max-force').value = config.max_force_g;
        }
    } catch (error) {
        console.error('Error loading sensor settings:', error);
    }
}

async function saveSensorSettings() {
    const statusDiv = document.getElementById('settings-status');

    const settings = {
        hit_start_g: parseFloat(document.getElementById('setting-hit-start').value),
        hit_end_g: parseFloat(document.getElementById('setting-hit-end').value),
        end_samples: parseInt(document.getElementById('setting-end-samples').value),
        max_force_g: parseFloat(document.getElementById('setting-max-force').value)
    };

    try {
        const response = await fetch(`${API_URL}/sensor/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (response.ok) {
            statusDiv.textContent = '✅ Settings saved successfully!';
            statusDiv.className = 'success';
            setTimeout(() => statusDiv.textContent = '', 3000);
        } else {
            statusDiv.textContent = '❌ Failed to save settings';
            statusDiv.className = 'error';
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        statusDiv.textContent = '❌ Error: ' + error.message;
        statusDiv.className = 'error';
    }
}

async function resetSensorSettings() {
    // Reset to default values
    document.getElementById('setting-hit-start').value = 0.7;
    document.getElementById('setting-hit-end').value = 0.3;
    document.getElementById('setting-end-samples').value = 5;
    document.getElementById('setting-max-force').value = 4.0;

    // Save the defaults
    await saveSensorSettings();
}

// ===== Debug Panel Functions =====

let debugPollingInterval = null;

function startDebugPolling() {
    if (debugPollingInterval) return;

    // Poll sensor status every 500ms
    debugPollingInterval = setInterval(updateDebugPanel, 500);
    updateDebugPanel(); // Update immediately
}

function stopDebugPolling() {
    if (debugPollingInterval) {
        clearInterval(debugPollingInterval);
        debugPollingInterval = null;
    }
}

async function updateDebugPanel() {
    try {
        // Fetch sensor status
        const response = await fetch(`${API_URL}/sensor/status`);

        if (response.ok) {
            const data = await response.json();

            // Update punch count
            document.getElementById('debug-punch-count').textContent = data.punch_count || 0;

            // Update monitoring status
            const monitoringSpan = document.getElementById('debug-monitoring');
            monitoringSpan.textContent = data.monitoring ? '✅ Active' : '❌ Inactive';
            monitoringSpan.style.color = data.monitoring ? 'green' : 'red';

            // Update last punch (if any)
            const lastPunchSpan = document.getElementById('debug-last-punch');
            if (data.last_punch) {
                lastPunchSpan.textContent = `${data.last_punch.force_g}g (force: ${data.last_punch.force_value})`;
            } else {
                lastPunchSpan.textContent = 'None';
            }

            // Display formatted sensor data with live acceleration
            const rawDataDiv = document.getElementById('debug-raw-data');
            if (data.current_accel) {
                const accel = data.current_accel;
                rawDataDiv.innerHTML = `
<strong>Live Acceleration (g-force):</strong>
  X-axis: ${accel.ax}g
  Y-axis: ${accel.ay}g
  Z-axis: ${accel.az}g
  Magnitude: ${accel.magnitude}g
  Dynamic (punch force): ${accel.dynamic}g

<strong>Thresholds:</strong>
  Hit Start: ${data.config.hit_start_g}g
  Hit End: ${data.config.hit_end_g}g
  Max Force: ${data.config.max_force_g}g

<strong>Status:</strong>
  ${data.monitoring ? '🟢 Monitoring active' : '🔴 Monitoring stopped'}
  ${accel.dynamic > data.config.hit_start_g ? '⚠️ PUNCH DETECTED!' : ''}
                `.trim();
            } else {
                rawDataDiv.textContent = JSON.stringify(data, null, 2);
            }

        } else {
            // Sensor API not responding
            document.getElementById('debug-monitoring').textContent = '⚠️ API Error';
            document.getElementById('debug-monitoring').style.color = 'orange';
            document.getElementById('debug-raw-data').textContent = `Error: ${response.status} ${response.statusText}`;
        }
    } catch (error) {
        console.error('Debug polling error:', error);
        document.getElementById('debug-monitoring').textContent = '❌ Disconnected';
        document.getElementById('debug-monitoring').style.color = 'red';
        document.getElementById('debug-raw-data').textContent = `Error: ${error.message}`;
    }
}

function updateIntensityDisplay() {
    const value = document.getElementById('char-intensity').value;
    document.getElementById('intensity-value').textContent = value;
}

function showModeChangeNotification(mode) {
    const modeNames = {
        'grunts': '🎤 Voice Grunts',
        'hit_sounds': '💥 Hit Sounds',
        'silent': '🔇 Silent'
    };

    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #667eea;
        color: white;
        padding: 15px 25px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 9999;
        animation: slideIn 0.3s ease;
        font-weight: 600;
    `;
    notification.textContent = `Switched to ${modeNames[mode]}`;

    document.body.appendChild(notification);

    // Remove after 2 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 2000);
}

async function loadVoices() {
    const voiceSelect = document.getElementById('char-voice');

    try {
        const response = await fetch(`${API_URL}/voices`);
        if (!response.ok) {
            throw new Error('Failed to fetch voices');
        }

        const data = await response.json();
        const voices = data.voices;

        // Clear existing options
        voiceSelect.innerHTML = '';

        // Add voices to dropdown
        voices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.id;
            option.textContent = voice.name;
            voiceSelect.appendChild(option);
        });

        console.log(`Loaded ${voices.length} voices`);
    } catch (error) {
        console.error('Error loading voices:', error);
        voiceSelect.innerHTML = '<option value="">Error loading voices</option>';
    }
}

async function cloneVoice() {
    const voiceName = document.getElementById('clone-voice-name').value;
    const voiceSample = document.getElementById('clone-voice-sample').files[0];
    const consent = document.getElementById('clone-consent-checkbox').checked;
    const statusDiv = document.getElementById('clone-status');

    // Validation
    if (!voiceName) {
        alert('Please enter a voice name');
        return;
    }
    if (!voiceSample) {
        alert('Please select an audio file');
        return;
    }
    if (!consent) {
        alert('You must confirm you have consent to clone this voice');
        return;
    }

    // Show loading status
    statusDiv.style.display = 'block';
    statusDiv.style.background = '#d1ecf1';
    statusDiv.style.color = '#0c5460';
    statusDiv.textContent = '🎤 Cloning voice... This may take 10-30 seconds.';

    // Disable button
    const submitBtn = document.getElementById('btn-submit-clone');
    submitBtn.disabled = true;

    try {
        const formData = new FormData();
        formData.append('voice_name', voiceName);
        formData.append('voice_sample', voiceSample);

        const response = await fetch(`${API_URL}/voices/clone`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            // Success!
            statusDiv.style.background = '#d4edda';
            statusDiv.style.color = '#155724';
            statusDiv.textContent = `✅ Voice "${voiceName}" cloned successfully!`;

            // Reload voices to show the new one
            await loadVoices();

            // Close modal after 2 seconds
            setTimeout(() => {
                document.getElementById('voice-clone-modal').style.display = 'none';
                // Reset form
                document.getElementById('clone-voice-name').value = '';
                document.getElementById('clone-voice-sample').value = '';
                document.getElementById('clone-consent-checkbox').checked = false;
                statusDiv.style.display = 'none';
            }, 2000);
        } else {
            throw new Error(result.error || 'Voice cloning failed');
        }
    } catch (error) {
        console.error('Error cloning voice:', error);
        statusDiv.style.background = '#f8d7da';
        statusDiv.style.color = '#721c24';
        statusDiv.textContent = `❌ Error: ${error.message}`;
    } finally {
        submitBtn.disabled = false;
    }
}

async function createCharacter() {
    // Build form data
    const formData = new FormData();
    formData.append('name', document.getElementById('char-name').value);
    formData.append('relationship', document.getElementById('char-relationship').value);
    formData.append('personality', document.getElementById('char-personality').value);
    formData.append('intensity', document.getElementById('char-intensity').value);
    formData.append('description', document.getElementById('char-description').value);
    formData.append('voice_id', document.getElementById('char-voice').value);

    // Hide form, show progress
    document.getElementById('form-create-character').style.display = 'none';
    document.getElementById('generation-progress').style.display = 'block';

    try {
        // For SSE via POST, we need to use fetch with streaming
        const response = await fetch(`${API_URL}/characters`, {
            method: 'POST',
            body: formData  // FormData auto-sets Content-Type with boundary
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.substring(6));
                    updateGenerationProgress(data);

                    if (data.status === 'completed') {
                        // Success!
                        setTimeout(() => {
                            document.getElementById('form-create-character').reset();
                            document.getElementById('form-create-character').style.display = 'block';
                            document.getElementById('generation-progress').style.display = 'none';
                            loadCharacters();
                            showScreen('selection');
                        }, 1000);
                    } else if (data.status === 'error') {
                        alert('Error creating character: ' + data.message);
                        document.getElementById('form-create-character').style.display = 'block';
                        document.getElementById('generation-progress').style.display = 'none';
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error creating character:', error);
        alert('Failed to create character');
        document.getElementById('form-create-character').style.display = 'block';
        document.getElementById('generation-progress').style.display = 'none';
    }
}

function updateGenerationProgress(data) {
    const progressFill = document.getElementById('progress-fill');
    const progressMessage = document.getElementById('progress-message');
    const progressTime = document.getElementById('progress-time');

    progressFill.style.width = `${data.progress}%`;
    progressMessage.textContent = data.message || data.status;

    // Estimate time remaining
    const remaining = Math.ceil((100 - data.progress) * 0.5); // Rough estimate
    if (remaining > 0) {
        progressTime.textContent = `Estimated: ${remaining} seconds remaining`;
    } else {
        progressTime.textContent = 'Almost done...';
    }
}

// ===== Workout Session =====

async function startWorkoutWithCharacter(characterId) {
    try {
        // Get feedback mode preference (default: grunts)
        const feedbackMode = localStorage.getItem('feedbackMode') || 'grunts';

        const response = await fetch(`${API_URL}/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                character_id: characterId,
                feedback_mode: feedbackMode
            })
        });

        currentSession = await response.json();

        // Set UI feedback mode selector
        document.getElementById('feedback-mode').value = feedbackMode;

        // Reset stats
        sessionStats = { punches: 0, totalForce: 0, maxForce: 0 };

        // Update UI
        document.getElementById('workout-character-name').textContent = `Fighting: ${currentSession.character_name}`;
        document.getElementById('punch-list').innerHTML = '';
        updateWorkoutStats();

        showScreen('workout');

        // Start debug polling automatically
        startDebugPolling();
    } catch (error) {
        console.error('Error starting workout:', error);
        alert('Failed to start workout');
    }
}

async function endWorkout() {
    if (!currentSession) return;

    try {
        await fetch(`${API_URL}/sessions/${currentSession.session_id}/end`, {
            method: 'POST'
        });

        alert(`Workout complete!\n${sessionStats.punches} punches\nMax force: ${sessionStats.maxForce.toFixed(1)}%`);

        currentSession = null;
        stopDebugPolling(); // Stop debug polling when workout ends
        showScreen('selection');
        loadCharacters(); // Refresh character list
    } catch (error) {
        console.error('Error ending workout:', error);
        alert('Failed to end workout');
    }
}

async function handlePunch(force) {
    if (!currentSession) {
        console.error('No active session');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/punch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSession.session_id,
                force: force
            })
        });

        const result = await response.json();

        // Update stats
        sessionStats.punches++;
        sessionStats.totalForce += result.force;
        sessionStats.maxForce = Math.max(sessionStats.maxForce, result.force);

        // Update UI
        updateWorkoutStats();
        displayTrashTalk(result.text);
        addPunchToHistory(result);

    } catch (error) {
        console.error('Error handling punch:', error);
    }
}

function updateWorkoutStats() {
    document.getElementById('stat-punches').textContent = sessionStats.punches;
    document.getElementById('stat-avg-force').textContent =
        sessionStats.punches > 0
            ? `${(sessionStats.totalForce / sessionStats.punches).toFixed(1)}%`
            : '0%';
    document.getElementById('stat-max-force').textContent = `${sessionStats.maxForce.toFixed(1)}%`;
}

function displayTrashTalk(text) {
    const display = document.getElementById('last-trash-talk');

    // Handle missing text (e.g., for grunts or undefined responses)
    if (!text || text === 'undefined') {
        return; // Don't update display for grunt-only feedback
    }

    display.textContent = `"${text}"`;

    // Animate
    display.style.animation = 'none';
    setTimeout(() => {
        display.style.animation = 'pulse 0.5s ease';
    }, 10);
}

function addPunchToHistory(punch) {
    const list = document.getElementById('punch-list');

    const item = document.createElement('div');
    item.className = `punch-item tier-${punch.tier}`;

    // Show feedback (grunt/hit sound) or text
    let displayText = punch.feedback || punch.text || '';

    // For hit sounds mode, show cleaner display
    if (punch.feedback_mode === 'hit_sounds' && displayText.startsWith('HIT')) {
        displayText = '💥 Impact';
    }

    item.innerHTML = `
        <div>
            <strong>Tier ${punch.tier}</strong> - ${punch.force.toFixed(1)}%
            ${punch.combo_count ? `<span style="color: #667eea; margin-left: 8px;">Combo x${punch.combo_count}</span>` : ''}
        </div>
        <div style="font-size: 0.85rem; color: #666;">
            ${displayText || 'Immediate feedback'}
        </div>
    `;

    list.insertBefore(item, list.firstChild);

    // Keep only last 10 punches visible
    while (list.children.length > 10) {
        list.removeChild(list.lastChild);
    }
}

// ===== Simulate Punch (for testing without hardware) =====

function simulatePunch() {
    // Random force between 0-1023 (weighted toward medium)
    const force = Math.random() * Math.random() * 1023;
    handlePunch(force);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }

    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
