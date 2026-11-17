const BASE_URL = 'http://localhost:8000/api/v1';

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = localStorage.getItem('token');

    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
    };

    const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });

    if (!response.ok) {
        // Пытаемся достать ошибку от FastAPI (там она в поле detail)
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Ошибка: ${response.status}`);
    }

    if (response.status === 204) return undefined as T;
    return response.json();
}