import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [organization, setOrganization] = useState(null);
  const [token, setToken] = useState(() => api.getToken());
  const [isLoading, setIsLoading] = useState(true);

  const fetchProfile = useCallback(async () => {
    const currentToken = api.getToken();
    if (!currentToken) {
      setOrganization(null);
      setIsLoading(false);
      return;
    }

    try {
      const data = await api.getMe();
      setOrganization(data);
    } catch (err) {
      console.warn('Session expired or invalid:', err.message);
      api.clearToken();
      setToken(null);
      setOrganization(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const login = async (registrationId, password, remember = true) => {
    const result = await api.login(registrationId, password);
    api.setToken(result.access_token, remember);
    setToken(result.access_token);
    setOrganization(result.organization);
    return result;
  };

  const logout = async () => {
    await api.logout();
    setToken(null);
    setOrganization(null);
  };

  const value = {
    organization,
    token,
    isAuthenticated: !!token && !!organization,
    isLoading,
    login,
    logout,
    refreshProfile: fetchProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
