'use client';

import { useAuth } from '@/lib/auth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export function withAuth<P extends object>(Component: React.ComponentType<P>) {
  return function AuthenticatedComponent(props: P) {
    const { user, loading, token } = useAuth();
    const router = useRouter();
    const [ready, setReady] = useState(false);

    useEffect(() => {
      if (!loading) {
        if (!user || !token) {
          router.push('/login');
        } else {
          setReady(true);
        }
      }
    }, [user, loading, token, router]);

    if (loading || !ready) {
      return (
        <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
          <div className="text-zinc-600">Loading...</div>
        </div>
      );
    }

    if (!user || !token) {
      return null;
    }

    return <Component {...props} />;
  };
}
