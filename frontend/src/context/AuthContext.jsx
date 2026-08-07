import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { apiFetch } from '../config';

const AuthContext = createContext(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

/**
 * Backend authentication API (hashed passwords, simple session)
 */

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('aduanflow_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const login = useCallback(async (username, password) => {
    try {
      const res = await apiFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (!res.ok) {
        // Return specific error info so LoginPage can display the right message
        let detail = 'Invalid credentials';
        try {
          const errData = await res.json();
          if (errData?.detail) detail = errData.detail;
        } catch {
          // ignore parse errors
        }
        return { success: false, error: detail };
      }
      const userData = await res.json();
      setUser(userData);
      localStorage.setItem('aduanflow_user', JSON.stringify(userData));
      return { success: true };
    } catch (e) {
      // Network error (backend unreachable)
      return { success: false, error: 'Unable to reach server. Please check your connection.' };
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('aduanflow_user');
  }, []);

  const isLoggedIn = !!user;

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoggedIn }}>
      {children}
    </AuthContext.Provider>
  );
}
