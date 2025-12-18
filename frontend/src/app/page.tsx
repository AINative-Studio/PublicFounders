import { redirect } from 'next/navigation';

export default function HomePage() {
  // Redirect to dashboard - auth will be handled there
  redirect('/dashboard');
}
