import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-4xl font-bold">SecureScope</h1>
      <p className="text-muted-foreground">사내 코드 정적 분석 대시보드</p>
      <Link href="/projects">
        <Button>프로젝트 목록</Button>
      </Link>
    </main>
  );
}
