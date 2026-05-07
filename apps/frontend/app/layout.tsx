import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SecureScope',
  description: '사내 코드 정적 분석 대시보드',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
