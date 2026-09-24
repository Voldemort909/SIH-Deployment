/**
 * Authentication and Session Management Utility for Frontend
 */

export const API_BASE = (() => {
    // If running in local dev with a separate frontend server (e.g. Live Server on port 5500/3000),
    // target the local Flask server at http://127.0.0.1:5000.
    const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocalhost && window.location.port !== "5000" && window.location.port !== "") {
        return "http://127.0.0.1:5000";
    }
    // When served by Flask on the same server (Render, cloud, or localhost:5000), use the same origin.
    return window.location.origin;
})();

const AUTH_API_BASE = API_BASE;

const TOKEN_KEY = "sih_placement_jwt_token";
const USER_KEY = "sih_placement_user_info";

export function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

export function getUser() {
    const raw = localStorage.getItem(USER_KEY);
    try {
        return raw ? JSON.parse(raw) : null;
    } catch (e) {
        return null;
    }
}

export function setUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function isAuthenticated() {
    return Boolean(getToken());
}

/**
 * Fetch wrapper that automatically injects the Bearer authorization token.
 */
export async function authFetch(endpoint, options = {}) {
    const token = getToken();
    const headers = {
        "Accept": "application/json",
        ...(options.headers || {})
    };

    // Only set application/json if body is NOT FormData (FormData needs browser-generated multipart boundary)
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    const url = endpoint.startsWith("http") ? endpoint : `${AUTH_API_BASE}${cleanEndpoint}`;
    return fetch(url, {
        ...options,
        headers
    });
}
