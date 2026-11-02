import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { mockApi } from '../api/mockApi';

export function RegisterPage() {
    const navigate = useNavigate();
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (password.length < 4) {
            setError('Пароль слишком короткий');
            return;
        }
        try {
            await mockApi.register(name, email, password);
            navigate('/works');
        } catch (err: any) {
            setError(err.message);
        }
    };

    return (
        <div style={{ maxWidth: 400, margin: '100px auto', padding: 20, border: '1px solid #ccc', borderRadius: 8 }}>
            <h2>Регистрация</h2>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <input type="text" placeholder="Имя" value={name} onChange={e => setName(e.target.value)} required style={{ padding: 8 }} />
                <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required style={{ padding: 8 }} />
                <input type="password" placeholder="Пароль" value={password} onChange={e => setPassword(e.target.value)} required style={{ padding: 8 }} />
                {error && <span style={{ color: 'red' }}>{error}</span>}
                <button type="submit" style={{ padding: 10, cursor: 'pointer' }}>Зарегистрироваться</button>
            </form>
            <p style={{ marginTop: 10 }}>Уже есть аккаунт? <Link to="/login">Войти</Link></p>
        </div>
    );
}