/**
 * Wildlife Intrusion Simulator - Frontend Application
 */

class SimulatorApp {
    constructor() {
        this.form = document.getElementById('simulationForm');
        this.submitBtn = document.getElementById('submitBtn');
        this.statusArea = document.getElementById('statusArea');
        this.resultsContent = document.getElementById('resultsContent');
        
        this.currentJobId = null;
        this.pollInterval = null;
        
        this.init();
    }
    
    init() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        // Gather form data
        const params = this.buildParams();
        
        // Disable submit button
        this.submitBtn.disabled = true;
        this.submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Submitting...';
        
        try {
            // Submit job
            const response = await fetch('/api/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentJobId = data.job_id;
                this.showPendingStatus();
                this.startPolling();
            } else {
                this.showError(data.error || 'Failed to submit job');
            }
        } catch (err) {
            this.showError('Network error: ' + err.message);
        }
        
        // Re-enable submit
        this.submitBtn.disabled = false;
        this.submitBtn.innerHTML = '<span class="btn-icon">▶</span> Run Simulation';
    }
    
    buildParams() {
        const getValue = (id, type = 'float') => {
            const el = document.getElementById(id);
            if (!el) return undefined;
            const val = el.value;
            return type === 'int' ? parseInt(val, 10) : parseFloat(val);
        };
        
        return {
            random_seed: getValue('randomSeed', 'int'),
            simulation: {
                event_count: getValue('eventCount', 'int'),
                intruder_probability: getValue('intruderProb')
            },
            topology: {
                outer_ring_nodes: getValue('outerNodes', 'int'),
                inner_ring_nodes: getValue('innerNodes', 'int'),
                sensor_range: getValue('sensorRange'),
                p2p_range: getValue('p2pRange')
            },
            decision_logic: {
                confirm_threshold: getValue('confirmThreshold'),
                verify_threshold: getValue('verifyThreshold'),
                verification_timeout: getValue('verifyTimeout')
            },
            image_model: {
                boar_confidence_mean: getValue('boarConfMean'),
                noise_confidence_mean: getValue('noiseConfMean')
            },
            communication: {
                loss_base: getValue('lossBase')
            },
            gateway: {
                up_duration_mean: getValue('gwUpMean')
            }
        };
    }
    
    showPendingStatus() {
        this.resultsContent.classList.add('hidden');
        this.statusArea.innerHTML = `
            <div class="status-pending">
                <div class="spinner"></div>
                <p>Job submitted. Waiting in queue...</p>
                <p class="job-id">Job ID: ${this.currentJobId}</p>
            </div>
        `;
    }
    
    showRunningStatus() {
        this.statusArea.innerHTML = `
            <div class="status-running">
                <span class="status-icon">🔄</span>
                <p>Simulation running...</p>
                <p class="job-id">Job ID: ${this.currentJobId}</p>
            </div>
        `;
    }
    
    showError(message) {
        this.statusArea.innerHTML = `
            <div class="status-failed">
                <span class="status-icon">❌</span>
                <p>Error: ${message}</p>
            </div>
        `;
        this.stopPolling();
    }
    
    startPolling() {
        this.pollInterval = setInterval(() => this.checkJobStatus(), 1500);
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    async checkJobStatus() {
        if (!this.currentJobId) return;
        
        try {
            const response = await fetch(`/api/jobs/${this.currentJobId}`);
            const data = await response.json();
            
            if (!data.success) {
                this.showError(data.error);
                return;
            }
            
            switch (data.status) {
                case 'pending':
                    // Still waiting
                    break;
                case 'running':
                    this.showRunningStatus();
                    break;
                case 'completed':
                    this.stopPolling();
                    await this.loadResults();
                    break;
                case 'failed':
                    this.stopPolling();
                    this.showError(data.error || 'Simulation failed');
                    break;
            }
        } catch (err) {
            console.error('Error checking status:', err);
        }
    }
    
    async loadResults() {
        try {
            const response = await fetch(`/api/jobs/${this.currentJobId}/results`);
            const data = await response.json();
            
            if (!data.success) {
                this.showError(data.error);
                return;
            }
            
            this.displayResults(data);
        } catch (err) {
            this.showError('Failed to load results: ' + err.message);
        }
    }
    
    displayResults(data) {
        const metrics = data.metrics;
        const summary = data.summary;
        
        // Update status area
        this.statusArea.innerHTML = `
            <div class="status-completed">
                <span class="status-icon">✅</span>
                <p>Simulation completed successfully</p>
            </div>
        `;
        
        // Update metric cards
        document.getElementById('detectionRate').textContent = 
            this.formatPercent(metrics.detection_rate);
        document.getElementById('fprValue').textContent = 
            this.formatPercent(metrics.false_positive_rate);
        document.getElementById('latencyValue').textContent = 
            `${metrics.mean_latency_seconds.toFixed(3)}s`;
        document.getElementById('p2pMessages').textContent = 
            metrics.total_p2p_messages;
        
        // Update plots
        const baseUrl = `/api/jobs/${this.currentJobId}/artifacts`;
        document.getElementById('latencyPlot').src = `${baseUrl}/latency_cdf.png`;
        document.getElementById('comparisonPlot').src = `${baseUrl}/detection_comparison.png`;
        document.getElementById('p2pPlot').src = `${baseUrl}/p2p_overhead.png`;
        
        // Update conclusion
        if (summary && summary.conclusion) {
            document.getElementById('conclusionText').textContent = summary.conclusion;
        }
        
        // Update download links
        document.getElementById('downloadMetrics').href = `${baseUrl}/metrics.json`;
        document.getElementById('downloadSummary').href = `${baseUrl}/summary.json`;
        document.getElementById('downloadInput').href = `${baseUrl}/input.json`;
        
        // Show results
        this.resultsContent.classList.remove('hidden');
    }
    
    formatPercent(value) {
        return `${(value * 100).toFixed(1)}%`;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new SimulatorApp();
});
