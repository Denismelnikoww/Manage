import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { WorksPage } from './pages/WorksPage';

export default function App() {
  return (
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/works" element={<WorksPage />} />
          <Route path="*" element={<Navigate to="/works" replace />} />
        </Routes>
      </BrowserRouter>
  );
}