import { request } from './client';

export type SubmissionStatus =
    | 'not_started'
    | 'in_progress'
    | 'submitted'
    | 'needs_work'
    | 'accepted';


export interface WorkResponse {
    id: number;
    order_num: number;
    title: string;
    description: string;
    deadline: string;
    group_name: string;
    is_deleted: boolean;
    created_at: string;
    updated_at: string;
    is_overdue: boolean;
    days_until_deadline: number | null;
    student_submission: {
        id: number;
        status: SubmissionStatus;
        submitted_at: string | null;
    } | null;
}

export interface WorkListResponse {
    total: number;
    items: WorkResponse[];
}

export interface CreateWorkRequest {
    order_num: number;
    title: string;
    description: string;
    deadline: string;
    group_name: string;
}

export const worksApi = {
    getWorks: (): Promise<WorkListResponse> => {
        return request<WorkListResponse>('/works');
    },

    createWork: (data: CreateWorkRequest): Promise<WorkResponse> => {
        return request<WorkResponse>('/works', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
};