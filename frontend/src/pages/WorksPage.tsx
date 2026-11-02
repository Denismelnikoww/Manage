import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Work, WorkStatus } from '../types';
import { mockApi } from '../api/mockApi';

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

    // Стейт для фильтра
    const [filter, setFilter] = useState<WorkStatus | 'ALL'>('ALL');

    // Стейты для формы создания
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
        loadWorks(); // перезапрашиваем список
    };

    const handleLogout = () => {
        localStorage.clear();
        navigate('/login');
    };

    if (loading) return <div style={{ padding: 20 }}>Загрузка...</div>;

    const filteredWorks = filter === 'ALL' ? works : works.filter(w => w.status === filter);

    return (
        <div style={{ padding: 20, maxWidth: 1000, margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <h2>Мои задачи</h2>
                <button onClick={handleLogout} style={{ padding: '8px 16px', cursor: 'pointer' }}>Выйти</button>
            </div>

            {/* Форма создания */}
            <div style={{ border: '1px solid #ccc', padding: 15, borderRadius: 8, marginBottom: 20, background: '#f0f8ff' }}>
                <h3>Создать задачу</h3>
                <form onSubmit={handleCreate} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    <input type="text" placeholder="Название" value={title} onChange={e => setTitle(e.target.value)} required style={{ padding: 8, flex: 1, minWidth: 200 }} />
                    <input type="text" placeholder="Описание" value={description} onChange={e => setDescription(e.target.value)} style={{ padding: 8, flex: 2, minWidth: 200 }} />
                    <input type="date" value={deadline} onChange={e => setDeadline(e.target.value)} required style={{ padding: 8 }} />
                    <button type="submit" style={{ padding: '8px 16px', cursor: 'pointer' }}>Добавить</button>
                </form>
            </div>

            {/* Фильтры */}
            <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                <button onClick={() => setFilter('ALL')} style={{ fontWeight: filter === 'ALL' ? 'bold' : 'normal' }}>Все</button>
                {Object.entries(STATUS_LABELS).map(([key, label]) => (
                    <button key={key} onClick={() => setFilter(key as WorkStatus)} style={{ fontWeight: filter === key ? 'bold' : 'normal' }}>
                        {label}
                    </button>
                ))}
            </div>

            {/* Сетка задач */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 15 }}>
                {filteredWorks.length === 0 ? <p>Задач нет</p> : filteredWorks.map(w => (
                    <div key={w.id} style={{ border: '1px solid #ddd', padding: 15, borderRadius: 8, background: '#fff', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                        <h3 style={{ margin: '0 0 10px 0' }}>{w.title}</h3>
                        <p style={{ margin: '0 0 10px 0', fontSize: 14, color: '#666' }}>{w.description || 'Без описания'}</p>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, alignItems: 'center' }}>
                            <strong>До: {w.deadline}</strong>
                            <span style={{ padding: '4px 8px', background: '#e0e0e0', borderRadius: 4, fontWeight: 'bold' }}>
                {STATUS_LABELS[w.status]}
              </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}