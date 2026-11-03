// ============================================================
// auth.js — Login & Register Page Logic
// ============================================================

document.addEventListener('DOMContentLoaded', function () {

    // ── Register Form Validation ──────────────────────────
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {

        const password = document.getElementById('password');
        const confirm  = document.getElementById('confirm_password');
        const matchMsg = document.getElementById('matchMsg');

        // Live password strength checker
        if (password) {
            password.addEventListener('input', function () {
                const strength = checkPasswordStrength(this.value);
                showPasswordStrength(strength);
            });
        }

        // Live password match checker
        if (confirm) {
            confirm.addEventListener('input', function () {
                if (password.value === this.value) {
                    matchMsg.innerHTML =
                        '<i class="fas fa-check text-success me-1"></i>' +
                        '<span class="text-success">Passwords match!</span>';
                } else {
                    matchMsg.innerHTML =
                        '<i class="fas fa-times text-danger me-1"></i>' +
                        '<span class="text-danger">Passwords do not match</span>';
                }
            });
        }

        // Form submit validation
        registerForm.addEventListener('submit', function (e) {
            const name  = document.querySelector('[name="full_name"]');
            const email = document.querySelector('[name="email"]');

            if (!name.value.trim()) {
                e.preventDefault();
                API.showAlert('Please enter your full name.', 'warning');
                name.focus();
                return;
            }

            if (!isValidEmail(email.value)) {
                e.preventDefault();
                API.showAlert('Please enter a valid email.', 'warning');
                email.focus();
                return;
            }

            if (password.value.length < 6) {
                e.preventDefault();
                API.showAlert(
                    'Password must be at least 6 characters.', 'warning'
                );
                password.focus();
                return;
            }

            if (password.value !== confirm.value) {
                e.preventDefault();
                API.showAlert('Passwords do not match!', 'danger');
                confirm.focus();
                return;
            }

            // Show loading on button
            const btn = registerForm.querySelector('[type="submit"]');
            API.showLoading(btn, 'Creating Account...');
        });
    }

    // ── Login Form ────────────────────────────────────────
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function () {
            const btn = loginForm.querySelector('[type="submit"]');
            API.showLoading(btn, 'Logging in...');
        });
    }

    // ── Helper: Validate Email Format ────────────────────
    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    // ── Helper: Check Password Strength ──────────────────
    function checkPasswordStrength(password) {
        let score = 0;
        if (password.length >= 6)  score++;
        if (password.length >= 10) score++;
        if (/[A-Z]/.test(password)) score++;
        if (/[0-9]/.test(password)) score++;
        if (/[^A-Za-z0-9]/.test(password)) score++;
        return score;
    }

    // ── Helper: Show Password Strength Bar ───────────────
    function showPasswordStrength(score) {
        const existing = document.getElementById('strengthBar');
        if (existing) existing.remove();

        const colors = ['', 'danger', 'danger', 'warning', 'info', 'success'];
        const labels = ['', 'Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];

        if (score === 0) return;

        const bar = document.createElement('div');
        bar.id    = 'strengthBar';
        bar.className = 'mt-1';
        bar.innerHTML = `
            <div class="progress" style="height: 4px;">
                <div class="progress-bar bg-${colors[score]}"
                     style="width: ${score * 20}%">
                </div>
            </div>
            <small class="text-${colors[score]}">
                ${labels[score]}
            </small>
        `;

        const pwField = document.getElementById('password');
        if (pwField) {
            pwField.parentElement.insertAdjacentElement('afterend', bar);
        }
    }

    // ── Show/Hide Password Toggle ─────────────────────────
    window.togglePassword = function () {
        const field = document.getElementById('passwordField');
        const icon  = document.getElementById('eyeIcon');
        if (!field) return;

        if (field.type === 'password') {
            field.type = 'text';
            icon.classList.replace('fa-eye', 'fa-eye-slash');
        } else {
            field.type = 'password';
            icon.classList.replace('fa-eye-slash', 'fa-eye');
        }
    };
});