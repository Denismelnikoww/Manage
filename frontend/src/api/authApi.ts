import { request } from './client';

// Типы (полностью совпадают с Pydantic-схемами бэкенда)
export interface UserResponse {
    id: number;
    email: string;
    full_name: string | null;
    group_name: string | null;
    telegram_id: number | null;
    is_active: boolean;
    role: { id: number; code: string; title: string };
    created_at: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
    user: UserResponse;
}

export interface RegisterRequest {
    email: string;
    password: string;
    full_name: string;
    role: 'student' | 'teacher';
    group_name?: string;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export const authApi = {
    login: (data: LoginRequest): Promise<TokenResponse> => {
        return request<TokenResponse>('/auth/login', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    register: (data: RegisterRequest): Promise<UserResponse> => {
        return request<UserResponse>('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    // получение профиля (жив ли токен)
    me: (): Promise<UserResponse> => {
        return request<UserResponse>('/auth/me');
    }
};