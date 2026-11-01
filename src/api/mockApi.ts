import type { Work, User } from '../types';

export const mockUser: User = {
    id: 'u-1', email: 'test@test.com', name: 'Виктор (Frontend)', role: 'employee'
};

const mockWorks: Work[] = [
    { id: 'w-1', title: 'Формы авторизации', description: 'Сверстать формы логина и регистрации', status: 'IN_PROGRESS', deadline: '2026-11-05' },
    { id: 'w-2', title: 'Интерфейс работ', description: 'Сделать список/доску для задач', status: 'TODO', deadline: '2026-11-08' },
];

const delay = (ms: number) => new Promise(res => setTimeout(res, ms));

export const mockApi = {
    login: async (email: string, password: string) => {
        await delay(400);
        if (password.length < 4) throw new Error('Пароль слишком короткий');
        localStorage.setItem('token', 'mock-token');
        localStorage.setItem('user', JSON.stringify(mockUser));
        return mockUser;
    },
    register: async (name: string, email: string, password: string) => {
        await delay(400);
        localStorage.setItem('token', 'mock-token');
        localStorage.setItem('user', JSON.stringify({ ...mockUser, name, email }));
        return mockUser;
    },
    getWorks: async () => {
        await delay(400);
        return mockWorks;
    }
};