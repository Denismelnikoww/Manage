import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { mockApi } from '../api/mockApi';
import './Auth.scss';

export function LoginPage() {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        try {
            await mockApi.login(email, password);
            navigate('/works');
        } catch (err: any) {
            setError(err.message);
        }
    };

    return (
        <div className="auth-container">
            <h2>Вход в систему</h2>
            <form onSubmit={handleSubmit}>
                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                />
                <input
                    type="password"
                    placeholder="Пароль"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                />
                {error && <span className="error-message">{error}</span>}
                <button type="submit">Войти</button>
            </form>
            <p>Нет аккаунта? <Link to="/register">Регистрация</Link></p>
        </div>
    );
}