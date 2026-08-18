import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { Location } from 'react-router-dom';
import { FormStack } from '../ui/FormStack';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import { InlineBanner } from '../ui/InlineBanner';
import { useAuth } from '../../hooks/useAuth';
import { getErrorMessage } from '../../lib/errors';

interface LocationState {
  from?: Location;
}

export function LoginForm() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ email, password });
      const state = location.state as LocationState | null;
      navigate(state?.from?.pathname ?? '/', { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, 'Invalid email or password.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <FormStack onSubmit={handleSubmit} gap={4} alignItems="stretch" w="full">
      {error && <InlineBanner status="error">{error}</InlineBanner>}
      <AnimatedInput
        label="Email"
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setEmail(event.target.value)}
      />
      <AnimatedInput
        label="Password"
        type="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setPassword(event.target.value)}
      />
      <GradientButton type="submit" isLoading={isSubmitting} w="full">
        Log in
      </GradientButton>
    </FormStack>
  );
}
