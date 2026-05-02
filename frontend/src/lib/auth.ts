import { encrypt, decrypt } from "./crypto";

let _accessToken: string | null = null;

export const setToken = async (token: string) => {
  console.log("setToken called with:", token ? "token exists" : "token null");
  _accessToken = token;
  
  try {
    const encrypted = await encrypt(token);
    console.log("encrypted:", encrypted ? "success" : "failed");
    sessionStorage.setItem("access_token", encrypted);
    console.log("sessionStorage set:", sessionStorage.getItem("access_token") ? "success" : "failed");
  } catch (error) {
    console.error("setToken error:", error);
  }
};
export const getToken = async (): Promise<string | null> => {
  if (_accessToken) return _accessToken;
  const stored = sessionStorage.getItem("access_token");
  if (stored) {
    const decrypted = await decrypt(stored)
    _accessToken = decrypted;
    return decrypted;
  }
  return null;
};

export const clearToken = () => {
  _accessToken = null;
  sessionStorage.removeItem("access_token");
};
