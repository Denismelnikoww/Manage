import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../api/authApi';
import './Auth.scss';

export function LoginPage() {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const data = await authApi.login({ email, password });
            // Сохраняем токен
            localStorage.setItem('token', data.access_token);
            // Сохраняем данные юзера (роль, имя и т.д.)
            localStorage.setItem('user', JSON.stringify(data.user));

            navigate('/works');
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <h2>Вход в систему</h2>
            <form onSubmit={handleSubmit}>
                <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required />
                <input type="password" placeholder="Пароль" value={password} onChange={e => setPassword(e.target.value)} required />
                {error && <span className="error-message">{error}</span>}
                <button type="submit" disabled={loading}>
                    {loading ? 'Загрузка...' : 'Войти'}
                </button>
            </form>
            <p>Нет аккаунта? <Link to="/register">Регистрация</Link></p>
        </div>
    );
}