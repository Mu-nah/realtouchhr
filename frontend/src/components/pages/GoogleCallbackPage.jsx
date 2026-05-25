import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export default function GoogleCallbackPage() {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const { refresh } = useAuth();

    useEffect(() => {
        const token = params.get('token');
        const error = params.get('error');

        if (error || !token) {
            navigate('/login?error=' + (error || 'google_failed'), { replace: true });
            return;
        }

        localStorage.setItem('token', token);
        refresh().then(() => navigate('/dashboard', { replace: true }));
    }, [params, navigate, refresh]);

    return (
        <div className="flex items-center justify-center min-h-screen">
            <p className="text-muted-foreground">Signing you in…</p>
        </div>
    );
}
