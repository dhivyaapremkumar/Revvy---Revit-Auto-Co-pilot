import { PageWrapper } from '../components/layout/PageWrapper';
import { DashboardHome } from '../components/dashboard/DashboardHome';
import { GuestHero } from '../components/dashboard/GuestHero';
import { useAuth } from '../hooks/useAuth';

export function HomePage() {
  const { user } = useAuth();

  return <PageWrapper>{user ? <DashboardHome /> : <GuestHero />}</PageWrapper>;
}
