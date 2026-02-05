// visualizer.js
let simulationData = null;
let isPlaying = false;
let currentTime = 0;
let playbackSpeed = 5; // Multiplier
let animationFrameId = null;
let lastFrameTime = 0;

// Config
const RADIUS_OUTER = 250;
const RADIUS_INNER = 150;
const CANVAS_SIZE = 600;
const CENTER_X = CANVAS_SIZE / 2;
const CENTER_Y = CANVAS_SIZE / 2;

// DOM Elements
const timeDisplay = document.getElementById('timeDisplay');
const eventList = document.getElementById('eventList');

async function loadData() {
    const response = await fetch('/data/log');
    simulationData = await response.json();
    initVisualization();
    renderCharts(simulationData); // Call function from charts.js
}

function initVisualization() {
    const svg = d3.select("#vis-container").append("svg")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("viewBox", `0 0 ${CANVAS_SIZE} ${CANVAS_SIZE}`)
        .append("g");

    // Draw Rings
    svg.append("circle")
        .attr("cx", CENTER_X).attr("cy", CENTER_Y)
        .attr("r", RADIUS_OUTER)
        .attr("fill", "none").attr("stroke", "#ddd").attr("stroke-width", 2);

    svg.append("circle")
        .attr("cx", CENTER_X).attr("cy", CENTER_Y)
        .attr("r", RADIUS_INNER)
        .attr("fill", "none").attr("stroke", "#ddd").attr("stroke-width", 2);

    // Prepare Node Data
    const nodes = Object.values(simulationData.metadata.nodes);

    // Calculate X,Y for each node
    nodes.forEach(node => {
        const r = node.ring === 'outer' ? RADIUS_OUTER : RADIUS_INNER;
        const rad = (node.angle * Math.PI) / 180;
        node.x = CENTER_X + r * Math.cos(rad);
        node.y = CENTER_Y + r * Math.sin(rad);
    });

    // Draw Nodes
    svg.selectAll(".node")
        .data(nodes)
        .enter().append("circle")
        .attr("class", "node-circle")
        .attr("id", d => `node-${d.id}`)
        .attr("cx", d => d.x)
        .attr("cy", d => d.y)
        .attr("r", 12)
        .attr("fill", "#95a5a6"); // Default Idle Color

    // Draw Labels
    svg.selectAll(".label")
        .data(nodes)
        .enter().append("text")
        .attr("x", d => d.x)
        .attr("y", d => d.y - 15)
        .attr("text-anchor", "middle")
        .attr("font-size", "10px")
        .attr("fill", "#555")
        .text(d => d.id);

    // Voting Lines Group
    svg.append("g").attr("id", "links-group");
}

function updateVisuals(time) {
    timeDisplay.innerText = `Time: ${time.toFixed(1)}s`;

    // Process Events up to current time (Cumulative or State-Based?)
    // For simplicity, we just look for events that "just happened" or reset states manually
    // Better approach for replay: Calculate state at Time T

    // 1. Reset all to IDLE first (simplification for robustness)
    // In a real app, we'd maintaining state machine. 
    // Here we find the *latest* state-change event for each node before current Time

    // Clear links
    d3.select("#links-group").selectAll("*").remove();
    const activeLinks = [];

    const nodes = Object.values(simulationData.metadata.nodes);

    nodes.forEach(node => {
        // Find last event for this node
        const relevantEvents = simulationData.events.filter(e =>
            (e.node_id === node.id || e.source_node === node.id) && e.time <= time
        );

        // Determine state color
        let color = "#95a5a6"; // Idle

        if (relevantEvents.length > 0) {
            const lastEvent = relevantEvents[relevantEvents.length - 1];

            // Map event types to states
            if (lastEvent.state) {
                if (lastEvent.state === "PIR_ACTIVE") color = "#f1c40f";
                else if (lastEvent.state === "THERMAL_ACTIVE") color = "#e67e22";
                else if (lastEvent.state === "CAMERA_PROCESSING") color = "#8e44ad";
                else if (lastEvent.state === "IDLE") color = "#95a5a6";
            } else if (lastEvent.type === "ALERT_TRIGGER") {
                color = "#e74c3c";
            }
        }

        d3.select(`#node-${node.id}`).attr("fill", color);
    });

    // Draw active voting links (transient, show for 0.5s)
    const recentVotes = simulationData.events.filter(e =>
        (e.type === "VOTE_REQUEST" || e.type === "VOTE_RESPONSE") &&
        e.time <= time && e.time > time - 0.5
    );

    recentVotes.forEach(e => {
        if (e.type === "VOTE_REQUEST") {
            const source = nodes.find(n => n.id === e.source_node);
            e.target_nodes.forEach(targetId => {
                const target = nodes.find(n => n.id === targetId);
                d3.select("#links-group").append("line")
                    .attr("x1", source.x).attr("y1", source.y)
                    .attr("x2", target.x).attr("y2", target.y)
                    .attr("stroke", "#8e44ad")
                    .attr("stroke-width", 2)
                    .attr("stroke-dasharray", "5,5");
            });
        }
    });

    // Update Event Log
    const recentEvents = simulationData.events.filter(e =>
        e.time <= time && e.time > time - 0.2 // Show events as they happen
    );
    recentEvents.forEach(e => {
        // Check if already logged to avoid dupes in this rough loop
        // (Skipped for simplicity, just appending)
        // Ideally utilize a pointer
    });

    // Simplified Log: Just rebuild the list for the last 5 events
    const pastEvents = simulationData.events.filter(e => e.time <= time);
    const last5 = pastEvents.slice(-5).reverse();

    eventList.innerHTML = "";
    last5.forEach(e => {
        const li = document.createElement("li");
        li.innerHTML = `<span class="time">[${e.time.toFixed(1)}]</span> ${e.type} - ${e.node_id || e.source_node}`;
        eventList.appendChild(li);
    });

}

// Playback Loop
function loop(timestamp) {
    if (!isPlaying) return;
    if (!lastFrameTime) lastFrameTime = timestamp;

    const delta = (timestamp - lastFrameTime) / 1000;
    lastFrameTime = timestamp;

    currentTime += delta * playbackSpeed;

    if (currentTime > simulationData.metadata.simulation_duration) {
        currentTime = 0; // Loop or Stop
        isPlaying = false;
        document.getElementById('playBtn').innerText = "Play";
    }

    updateVisuals(currentTime);
    animationFrameId = requestAnimationFrame(loop);
}

// Controls
document.getElementById('playBtn').onclick = () => {
    isPlaying = true;
    lastFrameTime = 0;
    animationFrameId = requestAnimationFrame(loop);
};
document.getElementById('pauseBtn').onclick = () => {
    isPlaying = false;
    cancelAnimationFrame(animationFrameId);
};
document.getElementById('resetBtn').onclick = () => {
    isPlaying = false;
    currentTime = 0;
    updateVisuals(0);
};

// Init
loadData();
