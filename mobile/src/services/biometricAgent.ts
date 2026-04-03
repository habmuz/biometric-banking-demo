import axios from 'axios';

const AGENT_BASE = 'https://api.alhabibi.org';

export interface AuthSuccess {
  status: 'authentication_success';
  access_token: string;
  token_type: string;
  expires_in: number;
  acr: string;
  message: string;
}

export interface AuthFailure {
  status: 'authentication_failed' | 'registration_failed';
  reason: string;
  retry_allowed: boolean;
}

export type AuthResult = AuthSuccess | AuthFailure;

function stripDataUrl(imageBase64: string): string {
  return imageBase64.includes(',') ? imageBase64.split(',')[1] : imageBase64;
}

export async function authenticateWithFace(
  username: string,
  imageBase64: string,
): Promise<AuthResult> {
  const image_b64 = stripDataUrl(imageBase64);
  const response = await axios.post<AuthResult>(
    `${AGENT_BASE}/auth/biometric`,
    { username, image_b64 },
    {
      timeout: 90000,
      validateStatus: (s) => s === 200 || s === 401,
    },
  );
  return response.data;
}

export async function registerWithFace(
  username: string,
  imageBase64: string,
): Promise<AuthResult> {
  const image_b64 = stripDataUrl(imageBase64);
  const response = await axios.post<AuthResult>(
    `${AGENT_BASE}/register/biometric`,
    { username, image_b64 },
    {
      timeout: 90000,
      validateStatus: (s) => s === 200 || s === 401,
    },
  );
  return response.data;
}

export async function checkIsRegistered(username: string): Promise<boolean> {
  try {
    const response = await axios.get<{ registered: boolean }>(
      `${AGENT_BASE}/users/${encodeURIComponent(username)}/registered`,
      { timeout: 5000 },
    );
    return response.data.registered;
  } catch {
    return false;
  }
}
