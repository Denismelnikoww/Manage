import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Work, WorkStatus } from '../types';
import { mockApi } from '../api/mockApi';
import './Works.scss';

const STATUS_LABELS: Record<WorkStatus, string> = {
    TODO: 'Нужно сделать',
    IN_PROGRESS: 'В работе',
    REVIEW: 'На проверке',
    DONE: 'Готово'
};

export function WorksPage() {
    const navigate = useNavigate();
    const [works, setWorks] = useState<Work[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<WorkStatus | 'ALL'>('ALL');

    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [deadline, setDeadline] = useState('');

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) {
            navigate('/login');
            return;
        }
        loadWorks();
    }, [navigate]);

    const loadWorks = () => {
        mockApi.getWorks().then(data => {
            setWorks(data);
            setLoading(false);
        });
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title || !deadline) return;
        await mockApi.createWork(title, description, deadline);
        setTitle('');
        setDescription('');
        setDeadline('');
        loadWorks();
    };

    const handleLogout = () => {
        localStorage.clear();
        navigate('/login');
    };

    if (loading) return <div className="loading">Загрузка...</div>;

    const filteredWorks = filter === 'ALL' ? works : works.filter(w => w.status === filter);

    return (
        <div className="works-container">
            <div className="works-header">
                <h2>Мои задачи</h2>
                <button onClick={handleLogout} className="secondary">Выйти</button>
            </div>

            <div className="create-work-panel">
                <h3>Создать задачу</h3>
                <form onSubmit={handleCreate}>
                    <input
                        type="text"
                        placeholder="Название"
                        value={title}
                        onChange={e => setTitle(e.target.value)}
                        required
                    />
                    <input
                        type="text"
                        placeholder="Описание"
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                    />
                    <input
                        type="date"
                        value={deadline}
                        onChange={e => setDeadline(e.target.value)}
                        required
                    />
                    <button type="submit">Добавить</button>
                </form>
            </div>

            <div className="filters-panel">
                <button
                    className={filter === 'ALL' ? 'active' : ''}
                    onClick={() => setFilter('ALL')}
                >
                    Все
                </button>
                {Object.entries(STATUS_LABELS).map(([key, label]) => (
                    <button
                        key={key}
                        className={filter === key ? 'active' : ''}
                        onClick={() => setFilter(key as WorkStatus)}
                    >
                        {label}
                    </button>
                ))}
            </div>

            <div className="works-grid">
                {filteredWorks.length === 0 ? (
                    <p>Задач нет</p>
                ) : (
                    filteredWorks.map(w => (
                        <div key={w.id} className="work-card">
                            <h3>{w.title}</h3>
                            <p>{w.description || 'Без описания'}</p>
                            <div className="work-footer">
                                <strong>До: {w.deadline}</strong>
                                <span className="status-badge">{STATUS_LABELS[w.status]}</span>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}