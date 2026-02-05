// charts.js

let batteryChartInstance = null;

function renderCharts(data) {
    const ctx = document.getElementById('batteryChart').getContext('2d');

    // Extract battery data
    const batteryData = data.metrics.battery;
    const labels = [0, 1, 2, 3, 4]; // Dummy time steps matching the array length in JSON

    const datasets = Object.keys(batteryData).map(nodeId => {
        return {
            label: nodeId,
            data: batteryData[nodeId],
            borderColor: nodeId.includes("outer") ? "#3498db" : "#2ecc71",
            borderWidth: 1,
            fill: false,
            tension: 0.4
        };
    });

    batteryChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            },
            scales: {
                y: { min: 99.8, max: 100.1 } // Zoom in for the sample data
            }
        }
    });

    // Update Latency Stats from JSON
    if (data.metrics.latency.length > 0) {
        document.getElementById('lat-val').innerText = data.metrics.latency[0].latency;
        document.getElementById('detect-count').innerText = data.metrics.latency.length;
    }
}
