// app.js
const socket = io();

// Config - must match backend
const CANVAS_SIZE = 600;
const CENTER_X = CANVAS_SIZE / 2;
const CENTER_Y = CANVAS_SIZE / 2;
const SCALE = 10; // pixels per meter

// Sensor geometry
const SENSOR_DEPTH = 10 * SCALE;  // 10m detection range (100px)
const SENSOR_FOV = 120;           // degrees (Increased for overlap)

// State map to Colors
const STATE_COLORS = {
    "IDLE": "#95a5a6",
    "PIR": "#f1c40f",       // Yellow
    "THERMAL": "#e67e22",   // Orange
    "CAMERA": "#3498db",    // Blue
    "VOTING": "#8e44ad",    // Purple
    "ALERT": "#e74c3c"      // Red
};

// Chart Setup
const ctx = document.getElementById('liveChart').getContext('2d');
const liveChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Detection Rate (%)',
                data: [],
                borderColor: '#2ecc71',
                tension: 0.4,
                fill: false,
                yAxisID: 'y'
            },
            {
                label: 'False Positive Rate (%)',
                data: [],
                borderColor: '#e74c3c',
                tension: 0.4,
                fill: false,
                yAxisID: 'y'
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
            x: { display: false },
            y: { min: 0, max: 100 }
        }
    }
});

// D3 Setup
const svg = d3.select("#vis-container").append("svg")
    .attr("width", "100%")
    .attr("height", "100%")
    .attr("viewBox", `0 0 ${CANVAS_SIZE} ${CANVAS_SIZE}`)
    .style("cursor", "crosshair");

// Groups (order matters for layering)
const gCoverage = svg.append("g"); // Coverage Layer (wedges)
const gRings = svg.append("g");
const gLinks = svg.append("g");
const gNodes = svg.append("g");

// Draw Rings (Static)
gRings.append("circle")
    .attr("cx", CENTER_X).attr("cy", CENTER_Y)
    .attr("r", 23 * SCALE).attr("fill", "none").attr("stroke", "#ddd").attr("stroke-width", 1).attr("stroke-dasharray", "4,4");
gRings.append("circle")
    .attr("cx", CENTER_X).attr("cy", CENTER_Y)
    .attr("r", 14 * SCALE).attr("fill", "none").attr("stroke", "#ddd").attr("stroke-width", 1).attr("stroke-dasharray", "4,4");

// D3 Arc Generator for FOV Wedges
const arcGenerator = d3.arc();

// Helper to create wedge path data
function createWedgePath(nodeAngle) {
    // Node angle is where the node sits on the ring (0 degrees = Right/East)
    // The wedge should point OUTWARD from the center.
    // SVG/D3 0 degrees is typically 12 o'clock or 3 o'clock depending on arc().
    // D3 arc() 0 is at 12 o'clock, but we position nodes using sin/cos where 0 is 3 o'clock.
    // Let's explicitly rotate the wedge to match the node's position relative to center.

    // We want the wedge center to align with nodeAngle.
    // Convert to radians.
    // Offset by -90 degrees (-PI/2) if D3 arc 0 is Up but our 0 is Right.
    // Actually, usually easier to generate a standard wedge centered at 0, and rotate the whole group.
    // But here we translate to x,y.

    // Let's try rotating the wedge by adding 90 degrees if it's currently tangent.
    // Original: (nodeAngle - 90/2) ... this assumes 0 is the direction of the node?
    // If nodes are at (r*cos(a), r*sin(a)), then angle 'a' is the direction FROM center TO node.
    // We want the wedge to point in direction 'a'.
    // D3 arc with 0 at 12 o'clock: 
    // We need to convert 'nodeAngle' (degrees) to the arc's expected angle system.

    const angleRad = (nodeAngle * Math.PI) / 180;

    // Create an arc centered at 0, facing "up" or "right", then we'll rotate it.
    // Actually, let's just use start/end angles relative to the node's angle.
    // We need to add 90 degrees (PI/2) because d3.arc 0 is usually 12 o'clock, and our 0 (Right) is 3 o'clock?
    // Let's try adding 90 degrees.
    const startAngle = angleRad - (SENSOR_FOV * Math.PI / 180) / 2 + Math.PI / 2;
    const endAngle = angleRad + (SENSOR_FOV * Math.PI / 180) / 2 + Math.PI / 2;

    return arcGenerator({
        innerRadius: 0,
        outerRadius: SENSOR_DEPTH,
        startAngle: startAngle,
        endAngle: endAngle
    });
}

// Interaction
svg.on("click", function (event) {
    const coords = d3.pointer(event);
    const x = coords[0] - CENTER_X;
    const y = coords[1] - CENTER_Y;

    // Animate click ripple
    svg.append("circle")
        .attr("cx", coords[0]).attr("cy", coords[1])
        .attr("r", 5).attr("stroke", "cyan").attr("fill", "none")
        .transition().duration(500)
        .attr("r", 50).attr("opacity", 0).remove();

    const type = document.getElementById('injectionType').value;

    socket.emit('inject_event', {
        x: x,
        y: y,
        type: type
    });
});

// Socket Events
socket.on('connect', () => {
    document.getElementById('connectionStatus').innerHTML = "🟢 Connected";
    document.getElementById('connectionStatus').style.color = "green";
});

socket.on('disconnect', () => {
    document.getElementById('connectionStatus').innerHTML = "🔴 Disconnected";
    document.getElementById('connectionStatus').style.color = "red";
});

socket.on('state_update', (data) => {
    renderNodes(data.nodes);
    updateAlertLevel(data.alert_level);
    updateChart(data.stats);
});

function updateChart(stats) {
    if (!stats) return;

    const now = new Date();
    const timeLabel = `${now.getHours()}:${now.getMinutes()}:${now.getSeconds()}`;

    if (liveChart.data.labels.length > 20) {
        liveChart.data.labels.shift();
        liveChart.data.datasets[0].data.shift();
        liveChart.data.datasets[1].data.shift();
    }

    liveChart.data.labels.push(timeLabel);
    liveChart.data.datasets[0].data.push(stats.detection_rate);
    liveChart.data.datasets[1].data.push(stats.fp_rate);
    liveChart.update();
}

socket.on('visualize_voting', (data) => {
    const sourceNode = d3.select(`#node-${data.source}`).datum();

    data.targets.forEach(targetId => {
        const targetSelection = d3.select(`#node-${targetId}`);
        if (!targetSelection.empty()) {
            const targetNode = targetSelection.datum();

            gLinks.append("line")
                .attr("x1", parseFloat(sourceNode.x) + CENTER_X)
                .attr("y1", parseFloat(sourceNode.y) + CENTER_Y)
                .attr("x2", parseFloat(targetNode.x) + CENTER_X)
                .attr("y2", parseFloat(targetNode.y) + CENTER_Y)
                .attr("stroke", "#8e44ad")
                .attr("stroke-width", 2)
                .attr("stroke-dasharray", "5,5")
                .transition().duration(500)
                .attr("opacity", 0)
                .remove();
        }
    });
});

socket.on('log_message', (data) => {
    const li = document.createElement("li");
    li.innerText = `[${new Date().toLocaleTimeString()}] ${data.msg}`;
    const list = document.getElementById("eventList");
    list.prepend(li);
    if (list.children.length > 20) list.lastChild.remove();
});

// Render Coverage Wedges
function renderCoverage(nodes) {
    const selection = gCoverage.selectAll(".fov-wedge").data(nodes, d => d.id);

    // Enter
    selection.enter().append("path")
        .attr("class", "fov-wedge")
        .attr("fill", d => d.id.startsWith("outer") ? "rgba(0, 100, 255, 0.25)" : "rgba(138, 43, 226, 0.25)") // Blue for outer, Violet for inner
        .attr("stroke", "none")
        .merge(selection)
        .attr("d", d => createWedgePath(d.angle))
        .attr("transform", d => `translate(${d.x + CENTER_X}, ${d.y + CENTER_Y})`);

    selection.exit().remove();
}

function renderNodes(nodes) {
    renderCoverage(nodes);

    const selection = gNodes.selectAll(".node-group").data(nodes, d => d.id);

    const enter = selection.enter().append("g")
        .attr("class", "node-group")
        .attr("id", d => `node-${d.id}`);

    enter.append("circle")
        .attr("r", 12)
        .attr("stroke", "#333")
        .attr("stroke-width", 1);

    enter.append("text")
        .attr("text-anchor", "middle")
        .attr("fill", "#333")
        .attr("y", 4)
        .style("font-size", "9px")
        .style("pointer-events", "none")
        .text(d => d.id.split('_')[1]);

    selection.merge(enter)
        .attr("transform", d => `translate(${d.x + CENTER_X}, ${d.y + CENTER_Y})`);

    const circles = selection.merge(enter).select("circle");

    circles.transition().duration(100)
        .attr("fill", d => STATE_COLORS[d.state] || "#95a5a6");

    circles.attr("class", d => {
        if (d.state === 'ALERT') return "blink-red";
        if (d.state === 'VOTING') return "blink-orange";
        return "";
    });

    selection.exit().remove();
}

function updateAlertLevel(level) {
    const el = document.getElementById('alertLevel');
    el.innerText = level;
    if (level === "NONE") el.className = "badge";
    else if (level === "LEVEL_1") el.className = "badge warning";
    else if (level === "LEVEL_2") el.className = "badge danger";
}
