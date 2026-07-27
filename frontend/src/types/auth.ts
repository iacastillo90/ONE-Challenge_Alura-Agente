export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user_id: string
  username: string
  refresh_token: string
  expires_at: string
  requires_2fa?: boolean
}

export interface RefreshResponse {
  access_token: string
  token_type: string
  refresh_token: string
  expires_at: string
}

export interface AuthState {
  token: string | null
  refreshToken: string | null
  userId: string | null
  username: string | null
  isAuthenticated: boolean
}

export const AUTH_KEYS = {
  token: "auth_token",
  refreshToken: "auth_refresh_token",
  userId: "auth_user_id",
  username: "auth_username",
} as const
