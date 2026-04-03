import { create } from 'zustand';
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

interface AuthState {
  accessToken: string | null;
  username: string | null;
  pdpaConsented: boolean;
  setToken: (token: string, username: string) => void;
  setPdpaConsented: (v: boolean) => void;
  logout: () => void;
  loadToken: () => Promise<void>;
}

const TOKEN_KEY = 'sc_access_token';
const USER_KEY = 'sc_username';

// Web fallback — SecureStore is native-only
const storage = {
  getItem: async (key: string): Promise<string | null> => {
    if (Platform.OS === 'web') return localStorage.getItem(key);
    return SecureStore.getItemAsync(key);
  },
  setItem: async (key: string, value: string): Promise<void> => {
    if (Platform.OS === 'web') { localStorage.setItem(key, value); return; }
    await SecureStore.setItemAsync(key, value);
  },
  deleteItem: async (key: string): Promise<void> => {
    if (Platform.OS === 'web') { localStorage.removeItem(key); return; }
    await SecureStore.deleteItemAsync(key);
  },
};

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  username: null,
  pdpaConsented: false,

  setToken: async (token, username) => {
    await storage.setItem(TOKEN_KEY, token);
    await storage.setItem(USER_KEY, username);
    set({ accessToken: token, username });
  },

  setPdpaConsented: (v) => set({ pdpaConsented: v }),

  logout: async () => {
    await storage.deleteItem(TOKEN_KEY);
    await storage.deleteItem(USER_KEY);
    set({ accessToken: null, username: null });
  },

  loadToken: async () => {
    const token = await storage.getItem(TOKEN_KEY);
    const username = await storage.getItem(USER_KEY);
    if (token && username) {
      set({ accessToken: token, username });
    }
  },
}));
