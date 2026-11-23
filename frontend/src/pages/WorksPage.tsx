import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { worksApi } from '../api/worksApi';
import type { WorkResponse } from '../api/worksApi';
import { submissionsApi, STATUS_LABELS } from '../api/submissionsApi';
import type { SubmissionStatus } from '../api/submissionsApi';
import './Works.scss';

export function WorksPage() {
    const navigate = useNavigate();
    const [works, setWorks] = useState<WorkResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Получаем инфу о юзере
    const userStr = localStorage.getItem('user');
    const user = userStr ? JSON.parse(userStr) : null;
    const isTeacher = user?.role?.code === 'teacher';

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) {
            navigate('/login');
            return;
        }
        loadWorks();
    }, [navigate]);

    const loadWorks = async () => {
        try {
            const data = await worksApi.getWorks();
            setWorks(data.items);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleStatusChange = async (submissionId: number, newStatus: SubmissionStatus, comment?: string) => {
        try {
            await submissionsApi.updateStatus(submissionId, newStatus, comment);
            // Перезапрашиваем список, чтобы увидеть обновленный статус
            loadWorks();
        } catch (err: any) {
            alert(`Ошибка: ${err.message}`);
        }
    };

    const handleLogout = () => {
        localStorage.clear();
        navigate('/login');
    };

    if (loading) return <div className="loading">Загрузка...</div>;
    if (error) return <div className="error-message" style={{ margin: 40, textAlign: 'center' }}>Ошибка: {error}</div>;

    return (
        <div className="works-container">
            <div className="works-header">
                <div>
                    <h2>Лабораторные работы</h2>
                    <span className="user-role">
                        {user?.full_name || user?.email} ({isTeacher ? 'Преподаватель' : 'Студент'})
                    </span>
                </div>
                <button onClick={handleLogout} className="secondary">Выйти</button>
            </div>

            <div className="works-grid">
                {works.length === 0 ? (
                    <p>Работ нет</p>
                ) : (
                    works.map(w => {
                        const sub = w.student_submission;

                        return (
                            <div key={w.id} className="work-card">
                                <div className="work-card-header">
                                    <h3>ЛР №{w.order_num}: {w.title}</h3>
                                    {w.is_overdue && <span className="badge-overdue">Просрочено</span>}
                                </div>
                                <p>{w.description}</p>

                                <div className="work-footer">
                                    <strong>До: {new Date(w.deadline).toLocaleDateString('ru-RU')}</strong>
                                    {sub ? (
                                        <span className="status-badge">{STATUS_LABELS[sub.status]}</span>
                                    ) : (
                                        <span className="status-badge teacher-view">Ведомость</span>
                                    )}
                                </div>

                                {/* --- Кнопки для Студента --- */}
                                {!isTeacher && sub && sub.status === 'not_started' && (
                                    <button
                                        className="btn-action student"
                                        onClick={() => handleStatusChange(sub.id, 'in_progress')}
                                    >
                                        Взять в работу
                                    </button>
                                )}

                                {/* --- Кнопки для Преподавателя --- */}
                                {/* Внимание: пока бэк не отдает список сдач для препода, эта кнопка появится только если он зайдет под студентом (для теста) */}
                                {isTeacher && sub && sub.status === 'submitted' && (
                                    <div className="teacher-actions">
                                        <button
                                            className="btn-action accept"
                                            onClick={() => handleStatusChange(sub.id, 'accepted')}
                                        >
                                            Принять
                                        </button>
                                        <button
                                            className="btn-action rework"
                                            onClick={() => {
                                                const comment = prompt('Введите комментарий (обязательно):');
                                                if (comment && comment.trim().length >= 5) {
                                                    handleStatusChange(sub.id, 'needs_work', comment);
                                                } else {
                                                    alert('Комментарий должен быть от 5 символов');
                                                }
                                            }}
                                        >
                                            На доработку
                                        </button>
                                    </div>
                                )}
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}