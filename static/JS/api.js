// ============================================================
// api.js — Central API Handler
// ============================================================

const API = {

    async post(url, data) {
        try {
            const res = await fetch(url, {
                method : 'POST',
                headers: {'Content-Type': 'application/json'},
                body   : JSON.stringify(data)
            });
            return await res.json();
        } catch(e) {
            console.error(`POST ${url} failed:`, e);
            return {success: false, message: e.message};
        }
    },

    async get(url) {
        try {
            const res = await fetch(url);
            return await res.json();
        } catch(e) {
            console.error(`GET ${url} failed:`, e);
            return {success: false, message: e.message};
        }
    },

    showAlert(message, type = 'info') {
        const existing = document.querySelector('.js-alert');
        if (existing) existing.remove();

        const icons = {
            success: 'fa-check-circle',
            danger : 'fa-times-circle',
            warning: 'fa-exclamation-triangle',
            info   : 'fa-info-circle'
        };

        const div = document.createElement('div');
        div.className = `alert alert-${type} alert-dismissible fade show js-alert`;
        div.innerHTML = `
            <i class="fas ${icons[type]||icons.info} me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        const main = document.querySelector('.main-content');
        if (main) main.insertAdjacentElement('afterbegin', div);
        setTimeout(() => div.remove(), 4000);
    },

    showLoading(btn, text = 'Loading...') {
        if (!btn) return;
        btn.disabled         = true;
        btn.dataset.original = btn.innerHTML;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${text}`;
    },

    hideLoading(btn) {
        if (!btn) return;
        btn.disabled  = false;
        btn.innerHTML = btn.dataset.original || 'Submit';
    }
};