const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  getToken() {
    return localStorage.getItem('resk_token') || sessionStorage.getItem('resk_token');
  }

  setToken(token, remember = true) {
    if (remember) {
      localStorage.setItem('resk_token', token);
      sessionStorage.removeItem('resk_token');
    } else {
      sessionStorage.setItem('resk_token', token);
      localStorage.removeItem('resk_token');
    }
  }

  clearToken() {
    localStorage.removeItem('resk_token');
    sessionStorage.removeItem('resk_token');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getToken();

    const headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    let data;
    try {
      data = await response.json();
    } catch {
      data = { message: 'Unexpected server response' };
    }

    if (!response.ok) {
      const errorMsg = data?.detail || data?.message || `Request failed with status ${response.status}`;
      const error = new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  }

  // --- Auth Endpoints ---

  async register(organizationData) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(organizationData),
    });
  }

  async sendVerificationCode(officialEmail) {
    return this.request('/auth/register/send-code', {
      method: 'POST',
      body: JSON.stringify({ official_email: officialEmail }),
    });
  }

  async verifyEmail({ token, email, code }) {
    const body = {};
    if (token) body.token = token;
    if (email) body.email = email;
    if (code) body.code = code;

    return this.request('/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async login(registrationId, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        registration_id: registrationId,
        password: password,
      }),
    });
  }

  async forgotPassword(companyEmail) {
    return this.request('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ company_email: companyEmail }),
    });
  }

  async resetPassword(resetToken, newPassword, confirmPassword) {
    return this.request('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({
        reset_token: resetToken,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });
  }

  async getMe() {
    return this.request('/auth/me', {
      method: 'GET',
    });
  }

  async logout() {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } catch {
      // Invalidate client side even if server token invalidation fails
    } finally {
      this.clearToken();
    }
  }
}

export const api = new ApiService();
