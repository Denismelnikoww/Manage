import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../api/authApi';
import './Auth.scss';

export function RegisterPage() {
    const navigate = useNavigate();
    const [form, setForm] = useState({
        full_name: '',
        email: '',
        password: '',
        role: 'student' as 'student' | 'teacher',
        group_name: 'ВПР42'
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setForm({ ...form, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await authApi.register({
                ...form,
                group_name: form.role === 'student' ? form.group_name : undefined
            });
            const loginRes = await authApi.login({ email: form.email, password: form.password });
            localStorage.setItem('token', loginRes.access_token);
            localStorage.setItem('user', JSON.stringify(loginRes.user));
            navigate('/works');
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <h2>Регистрация</h2>
            <form onSubmit={handleSubmit}>
                <input name="full_name" type="text" placeholder="ФИО" value={form.full_name} onChange={handleChange} required />
                <input name="email" type="email" placeholder="Email" value={form.email} onChange={handleChange} required />
                <input name="password" type="password" placeholder="Пароль (мин. 8 символов)" value={form.password} onChange={handleChange} required minLength={8} />

                <select name="role" value={form.role} onChange={handleChange} className="role-select">
                    <option value="student">Студент</option>
                    <option value="teacher">Преподаватель</option>
                </select>

                {form.role === 'student' && (
                    <input name="group_name" type="text" placeholder="Группа" value={form.group_name} onChange={handleChange} required />
                )}

                {error && <span className="error-message">{error}</span>}
                <button type="submit" disabled={loading}>
                    {loading ? 'Создание...' : 'Зарегистрироваться'}
                </button>
            </form>
            <p>Уже есть аккаунт? <Link to="/login">Войти</Link></p>
        </div>
    );
}