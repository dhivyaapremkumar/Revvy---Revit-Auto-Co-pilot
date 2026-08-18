import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { FormStack } from '../ui/FormStack';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import { InlineBanner } from '../ui/InlineBanner';
import { useAuth } from '../../hooks/useAuth';
import { getErrorMessage } from '../../lib/errors';

export function RegisterForm() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await register({ email, password, full_name: fullName || undefined });
      navigate('/', { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, 'Could not create your account.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <FormStack onSubmit={handleSubmit} gap={4} alignItems="stretch" w="full">
      {error && <InlineBanner status="error">{error}</InlineBanner>}
      <AnimatedInput
        label="Full name"
        type="text"
        autoComplete="name"
        value={fullName}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setFullName(event.target.value)}
      />
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
        autoComplete="new-password"
        required
        minLength={8}
        value={password}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setPassword(event.target.value)}
      />
      <AnimatedInput
        label="Confirm password"
        type="password"
        autoComplete="new-password"
        required
        minLength={8}
        value={confirmPassword}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setConfirmPassword(event.target.value)}
      />
      <GradientButton type="submit" isLoading={isSubmitting} w="full">
        Create account
      </GradientButton>
    </FormStack>
  );
}
