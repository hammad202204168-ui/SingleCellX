/**
 * SingleCellX API Client - Enhanced Version
 * 
 * Provides high-level methods for interacting with the backend API:
 * - Authentication
 * - Project management
 * - Dataset operations
 * - Analysis execution
 * - Result export
 * - Batch operations
 */

class SingleCellXClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL || window.location.origin;
        this.token = localStorage.getItem('token');
        this.userId = localStorage.getItem('user_id');
        this.pollInterval = 2000; // ms between status polls
    }

    // ============================================================
    // Authentication
    // ============================================================

    async register(email, username, fullName, password) {
        const response = await fetch(`${this.baseURL}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, username, full_name: fullName, password }),
        });
        return this._handleResponse(response);
    }

    async login(username, password) {
        const response = await fetch(`${this.baseURL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        const data = await this._handleResponse(response);
        if (data.access_token) {
            this.token = data.access_token;
            this.userId = data.user.id;
            localStorage.setItem('token', this.token);
            localStorage.setItem('user_id', this.userId);
        }
        return data;
    }

    logout() {
        this.token = null;
        this.userId = null;
        localStorage.removeItem('token');
        localStorage.removeItem('user_id');
    }

    // ============================================================
    // Projects
    // ============================================================

    async listProjects() {
        return this._get('/api/projects');
    }

    async createProject(name, description = '') {
        return this._post('/api/projects', { name, description });
    }

    async getProject(projectId) {
        return this._get(`/api/projects/${projectId}`);
    }

    async updateProject(projectId, name, description) {
        return this._put(`/api/projects/${projectId}`, { name, description });
    }

    async deleteProject(projectId) {
        return this._delete(`/api/projects/${projectId}`);
    }

    // ============================================================
    // Datasets
    // ============================================================

    async uploadDataset(projectId, file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(
            `${this.baseURL}/api/projects/${projectId}/datasets/upload`,
            {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${this.token}` },
                body: formData,
            }
        );
        return this._handleResponse(response);
    }

    async listDatasets(projectId) {
        return this._get(`/api/projects/${projectId}/datasets`);
    }

    async createDemoDataset(projectId, name = 'Demo Dataset') {
        return this._post(`/api/projects/${projectId}/datasets/demo`, { name });
    }

    async getDataset(datasetId) {
        return this._get(`/api/datasets/${datasetId}`);
    }

    async deleteDataset(datasetId) {
        return this._delete(`/api/datasets/${datasetId}`);
    }

    // ============================================================
    // Analysis
    // ============================================================

    async startAnalysis(datasetId, name, parameters = {}) {
        return this._post('/api/analysis', {
            dataset_id: datasetId,
            name,
            parameters,
        });
    }

    async listAnalyses(projectId) {
        return this._get(`/api/projects/${projectId}/analysis`);
    }

    async getAnalysis(runId) {
        return this._get(`/api/analysis/${runId}`);
    }

    async getAnalysisLogs(runId, limit = 200) {
        return this._get(`/api/analysis/${runId}/logs?limit=${limit}`);
    }

    async getAnalysisResults(runId) {
        return this._get(`/api/analysis/${runId}/results`);
    }

    async deleteAnalysis(runId) {
        return this._delete(`/api/analysis/${runId}`);
    }

    /**
     * Poll for analysis completion
     * @param {number} runId - Analysis run ID
     * @param {function} onProgress - Callback with (status, progress, currentStep)
     * @param {function} onComplete - Callback with final results
     * @param {function} onError - Callback with error
     * @param {number} timeout - Max polling time in ms (0 = no limit)
     */
    async pollAnalysis(runId, onProgress, onComplete, onError, timeout = 0) {
        const startTime = Date.now();

        const poll = async () => {
            try {
                const run = await this.getAnalysis(runId);

                if (onProgress) {
                    onProgress(run.status, run.progress, run.current_step);
                }

                if (run.status === 'completed') {
                    const results = await this.getAnalysisResults(runId);
                    if (onComplete) onComplete(results);
                } else if (run.status === 'failed') {
                    if (onError) onError(run.error_message);
                } else {
                    // Still running, schedule next poll
                    if (timeout > 0 && Date.now() - startTime > timeout) {
                        if (onError) onError('Polling timeout');
                    } else {
                        setTimeout(poll, this.pollInterval);
                    }
                }
            } catch (error) {
                if (onError) onError(error.message);
            }
        };

        poll();
    }

    // ============================================================
    // Export
    // ============================================================

    async getExportManifest(runId) {
        return this._get(`/api/analysis/${runId}/export/manifest`);
    }

    downloadExport(runId, format) {
        const urls = {
            'markers': `/api/analysis/${runId}/export/markers.csv`,
            'umap': `/api/analysis/${runId}/export/embeddings-umap.csv`,
            'tsne': `/api/analysis/${runId}/export/embeddings-tsne.csv`,
            'pca': `/api/analysis/${runId}/export/pca-variance.csv`,
            'clusters': `/api/analysis/${runId}/export/cell-clusters.csv`,
            'qc': `/api/analysis/${runId}/export/qc-summary.csv`,
            'json': `/api/analysis/${runId}/export/results.json`,
        };

        if (!urls[format]) throw new Error(`Unknown export format: ${format}`);

        const url = `${this.baseURL}${urls[format]}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = `run_${runId}_${format}`;
        link.setAttribute('Authorization', `Bearer ${this.token}`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // ============================================================
    // Utilities
    // ============================================================

    async getHealth() {
        return this._get('/api/health');
    }

    async _get(path) {
        const response = await fetch(`${this.baseURL}${path}`, {
            headers: { 'Authorization': `Bearer ${this.token}` },
        });
        return this._handleResponse(response);
    }

    async _post(path, data) {
        const response = await fetch(`${this.baseURL}${path}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`,
            },
            body: JSON.stringify(data),
        });
        return this._handleResponse(response);
    }

    async _put(path, data) {
        const response = await fetch(`${this.baseURL}${path}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`,
            },
            body: JSON.stringify(data),
        });
        return this._handleResponse(response);
    }

    async _delete(path) {
        const response = await fetch(`${this.baseURL}${path}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${this.token}` },
        });
        return this._handleResponse(response);
    }

    async _handleResponse(response) {
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const error = data.detail || data.message || response.statusText;
            throw new Error(error);
        }

        return data;
    }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SingleCellXClient;
}
