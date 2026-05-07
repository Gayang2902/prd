import type { Metadata } from 'next';
import './globals.css';
import { Geist } from 'next/font/google';
import { cn } from '@/lib/utils';
import { Providers } from '@/components/providers';
import { OnboardingModal } from '@/components/onboarding-modal';

const geist = Geist({ subsets: ['latin'], variable: '--font-sans' });

export const metadata: Metadata = {
  title: 'SecureScope',
  description: '사내 코드 정적 분석 대시보드',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={cn('font-sans', geist.variable)}>
      <body>
        <Providers>
          {children}
          <OnboardingModal />
        </Providers>
      </body>
    </html>
  );
}
