import { AlertCircle } from 'lucide-react';

interface LoginFormErrorProps {
  message: string;
}

export function LoginFormError({ message }: LoginFormErrorProps) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2.5 rounded-md border border-danger/25 bg-dangerSoft px-3 py-2.5 text-sm text-danger"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
