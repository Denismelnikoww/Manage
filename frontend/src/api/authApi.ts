

const BASE_URL = 'http://localhost:8000/api/v1';

export interface LoginRequest {
    email: string;
    password: string;
}

export interface RegisterRequest {
    email: string;
    password: string;
    full_name: string;
    role: 'student' | 'teacher';
    group_name?: string;
}

export interface UserResponse {
    id: number;
    email: string;
    full_name: string | null;
    group_name: string | null;
    role: {
        id: number;
        code: string;
        title: string;
    };
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
    user: UserResponse;
}

export const authApi = {
    login: async (data: LoginRequest): Promise<AuthResponse> => {
        const response = await fetch(`${BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Ошибка при входе');
        }
        return response.json();
    },

    register: async (data: RegisterRequest): Promise<UserResponse> => {
        const response = await fetch(`${BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Ошибка при регистрации');
        }
        return response.json();
    },
};