import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { worksApi } from '../api/worksApi';
import type { WorkResponse, SubmissionStatus } from '../api/worksApi';
import './Works.scss';

const STATUS_LABELS: Record<SubmissionStatus, string> = {
    not_started: 'Не начата',
    in_progress: 'В работе',
    submitted: 'Сдана',
    needs_work: 'На доработке',
    accepted: 'Принята'
};

export function WorksPage() {
    const navigate = useNavigate();
    const [works, setWorks] = useState<WorkResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [filter, setFilter] = useState<SubmissionStatus | 'ALL'>('ALL');

    // Получаем инфу о юзере для рендера ролей
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

    const handleLogout = () => {
        localStorage.clear();
        navigate('/login');
    };

    if (loading) return <div className="loading">Загрузка...</div>;
    if (error) return <div className="error-message" style={{ margin: 40, textAlign: 'center' }}>Ошибка: {error}</div>;

    // Фильтрация: у преподавателя нет student_submission, поэтому фильтруем только если это студент
    const filteredWorks = works.filter(w => {
        if (filter === 'ALL') return true;
        // Если у преподавателя нет сдачи, показываем все, либо адаптируем под его логику
        if (isTeacher) return true;
        return w.student_submission?.status === filter;
    });

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

            <div className="filters-panel">
                <button className={filter === 'ALL' ? 'active' : ''} onClick={() => setFilter('ALL')}>Все</button>
                {Object.entries(STATUS_LABELS).map(([key, label]) => (
                    <button key={key} className={filter === key ? 'active' : ''} onClick={() => setFilter(key as SubmissionStatus)}>
                        {label}
                    </button>
                ))}
            </div>

            <div className="works-grid">
                {filteredWorks.length === 0 ? (
                    <p>Работ нет</p>
                ) : (
                    filteredWorks.map(w => (
                        <div key={w.id} className="work-card">
                            <div className="work-card-header">
                                <h3>ЛР №{w.order_num}: {w.title}</h3>
                                {w.is_overdue && <span className="badge-overdue">Просрочено</span>}
                            </div>
                            <p>{w.description}</p>

                            <div className="work-footer">
                                <strong>До: {new Date(w.deadline).toLocaleDateString('ru-RU')}</strong>
                                {w.student_submission ? (
                                    <span className="status-badge">{STATUS_LABELS[w.student_submission.status]}</span>
                                ) : (
                                    <span className="status-badge teacher-view">Ведомость</span>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}