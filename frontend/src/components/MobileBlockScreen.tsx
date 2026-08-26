import { MonitorSmartphone } from 'lucide-react';

export function MobileBlockScreen() {
  return (
    <div className="mobile-block">
      <div className="flex max-w-sm flex-col items-center gap-4 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-navy/10 text-navy">
          <MonitorSmartphone className="h-8 w-8" />
        </div>
        <h1 className="text-xl font-bold text-ink">Desktop Required</h1>
        <p className="text-sm leading-relaxed text-muted">
          StudioERP is designed for laptop and desktop screens.
          Please open this page on a device with a wider display.
        </p>
      </div>
    </div>
  );
}
