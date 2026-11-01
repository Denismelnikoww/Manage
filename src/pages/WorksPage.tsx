import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Work } from '../types';
import { mockApi } from '../api/mockApi';

export function WorksPage() {
    const navigate = useNavigate();
    const [works, setWorks] = useState<Work[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) {
            navigate('/login');
            return;
        }
        mockApi.getWorks().then(data => {
            setWorks(data);
            setLoading(false);
        });
    }, [navigate]);

    const handleLogout = () => {
        localStorage.clear();
        navigate('/login');
    };

    if (loading) return <div style={{ padding: 20 }}>Загрузка...</div>;

    return (
        <div style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>Мои задачи</h2>
                <button onClick={handleLogout} style={{ padding: '8px 16px', cursor: 'pointer' }}>Выйти</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 15, marginTop: 20 }}>
                {works.map(w => (
                    <div key={w.id} style={{ border: '1px solid #ddd', padding: 15, borderRadius: 8, background: '#f9f9f9', color: '#333' }}>
                        <h3 style={{ margin: '0 0 10px 0' }}>{w.title}</h3>
                        <p style={{ margin: '0 0 10px 0', fontSize: 14, color: '#666' }}>{w.description}</p>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                            <strong>Дедлайн: {w.deadline}</strong>
                            <span style={{ padding: '2px 6px', background: '#e0e0e0', borderRadius: 4 }}>{w.status}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}