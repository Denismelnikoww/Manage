export type WorkStatus = 'TODO' | 'IN_PROGRESS' | 'REVIEW' | 'DONE';

export interface User {
    id: string;
    email: string;
    name: string;
    role: 'admin' | 'manager' | 'employee';
}

export interface Work {
    id: string;
    title: string;
    description: string;
    status: WorkStatus;
    deadline: string;
}