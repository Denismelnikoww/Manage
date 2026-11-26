import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { worksApi } from '../api/worksApi';
import type { WorkResponse } from '../api/worksApi';
import { STATUS_LABELS } from '../api/submissionsApi';
import './Works.scss';


const MOCK_REPORTS = [
    { id: 1, version: 1, name: 'Отчет_ЛР1_v1.pdf', date: '2026-11-20 14:30' },
    { id: 2, version: 2, name: 'Отчет_ЛР1_исправленный.pdf', date: '2026-11-22 10:15' }
];

const MOCK_COMMENTS = [
    { id: 1, author: 'Преподаватель', text: 'В разделе 2 не хватает вывода. Исправьте.', date: '2026-11-21 12:00' },
    { id: 2, author: 'Студент', text: 'Исправил, прикрепил новую версию.', date: '2026-11-22 10:16' }
];

export function WorksPage() {
    const navigate = useNavigate();
    const [works, setWorks] = useState<WorkResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Состояние модального окна
    const [selectedWork, setSelectedWork] = useState<WorkResponse | null>(null);
    const [newComment, setNewComment] = useState('');

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

    const closeModal = () => setSelectedWork(null);

    const handleMockAction = (action: string) => {
        alert(`Кнопка "${action}" нажата. (Интеграция с API будет в задаче 4.4.5)`);
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
                {works.map(w => (
                    <div key={w.id} className="work-card">
                        <div className="work-card-header">
                            <h3>ЛР №{w.order_num}: {w.title}</h3>
                        </div>
                        <p>{w.description}</p>
                        <div className="work-footer">
                            <strong>До: {new Date(w.deadline).toLocaleDateString('ru-RU')}</strong>
                            {w.student_submission && (
                                <span className="status-badge">{STATUS_LABELS[w.student_submission.status]}</span>
                            )}
                        </div>
                        {w.student_submission && (
                            <button className="btn-action student" onClick={() => setSelectedWork(w)}>
                                Открыть карточку сдачи
                            </button>
                        )}
                    </div>
                ))}
            </div>

            {/* --- ИНТЕРФЕЙС МОДАЛЬНОГО ОКНА --- */}
            {selectedWork && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Сдача по работе: {selectedWork.title}</h3>
                            <button className="close-btn" onClick={closeModal}>×</button>
                        </div>

                        <div className="modal-body">
                            {/* Блок 1: Загрузка файла (только для студента) */}
                            {!isTeacher && (
                                <div className="submission-info">
                                    <h4>Загрузка отчета</h4>
                                    <p style={{ fontSize: 12, color: '#666' }}>Форматы: PDF, DOCX, ZIP (до 20 МБ)</p>
                                    <div className="upload-section">
                                        <input type="file" id="file-upload" style={{ display: 'none' }} />
                                        <button className="btn-action student" onClick={() => handleMockAction('Загрузка файла')}>
                                            Выбрать файл и загрузить
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* Блок 2: История версий отчетов */}
                            <div className="reports-section">
                                <h4>История версий отчета</h4>
                                <div className="reports-list">
                                    {MOCK_REPORTS.map(rep => (
                                        <div key={rep.id} className="report-item">
                                            <div>
                                                <strong>Версия {rep.version}</strong> ({rep.name})
                                                <small>{rep.date}</small>
                                            </div>
                                            <button className="btn-action" onClick={() => handleMockAction('Скачивание')}>
                                                Скачать
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Блок 3: Комментарии */}
                            <div className="comments-section">
                                <h4>Комментарии и замечания</h4>
                                <div className="comments-list">
                                    {MOCK_COMMENTS.map(c => (
                                        <div key={c.id} className="comment-item">
                                            <strong>{c.author}:</strong>
                                            <p>{c.text}</p>
                                            <span className="comment-date">{c.date}</span>
                                        </div>
                                    ))}
                                </div>

                                {/* Форма для преподавателя */}
                                {isTeacher && (
                                    <form className="comment-form" onSubmit={(e) => { e.preventDefault(); handleMockAction('Отправка комментария'); setNewComment(''); }}>
                                        <textarea
                                            value={newComment}
                                            onChange={e => setNewComment(e.target.value)}
                                            placeholder="Оставьте комментарий (мин. 5 символов)..."
                                            required
                                            minLength={5}
                                        />
                                        <button type="submit" className="btn-action accept">Отправить</button>
                                    </form>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}