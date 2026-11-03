import type { ReactNode } from 'react';
import { COMPANY } from '../company';

export const LegalPage = ({ title, children }: { title: string; children: ReactNode }) => (
  <article className="space-y-5 text-gray-700 leading-relaxed">
    <header>
      <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
      <p className="mt-1 text-sm text-gray-500">Effective {COMPANY.policyEffectiveDate}</p>
    </header>
    {children}
  </article>
);

export const H2 = ({ children }: { children: ReactNode }) => (
  <h2 className="text-lg font-semibold text-gray-900 pt-2">{children}</h2>
);

export const Ul = ({ children }: { children: ReactNode }) => (
  <ul className="list-disc pl-6 space-y-1">{children}</ul>
);
