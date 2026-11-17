import { request } from './client';

export type SubmissionStatus =
    | 'not_started'
    | 'in_progress'
    | 'submitted'
    | 'needs_work'
    | 'accepted';

export const STATUS_LABELS: Record<SubmissionStatus, string> = {
    not_started: 'Не начата',
    in_progress: 'В работе',
    submitted: 'Сдана',
    needs_work: 'На доработке',
    accepted: 'Принята',
};

export const submissionsApi = {
    updateStatus: (
        submissionId: number,
        status: SubmissionStatus,
        commentText?: string
    ) => {
        return request(`/submissions/${submissionId}/status`, {
            method: 'PATCH',
            body: JSON.stringify({ status, comment_text: commentText }),
        });
    },
};