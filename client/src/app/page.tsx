'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';
import { useSampleQuery } from '@/hooks/queries/use-sample-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function Home() {
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const { data, error, isFetching } = useSampleQuery(submittedQuery);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmittedQuery(query.trim());
  }

  let output = '결과가 여기에 표시됩니다.';

  if (isFetching) {
    output = '요청 중...';
  } else if (error) {
    output = JSON.stringify({ error: error.message }, null, 2);
  } else if (data) {
    output = JSON.stringify(data, null, 2);
  }

  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-6 py-10">
      <h1 className="gradient-text mb-8 text-3xl font-bold">SandboxIA</h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="query">Query</Label>
          <Input
            id="query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="검색할 쿼리를 입력하세요"
          />
        </div>

        <Button type="submit" variant="gradient" disabled={isFetching} className="w-full">
          {isFetching ? '요청 중...' : '검색'}
        </Button>
      </form>

      <section className="mt-8">
        <Label className="mb-2 block">Response</Label>
        <pre className="min-h-[200px] whitespace-pre-wrap rounded-md border border-border bg-muted p-4 text-sm text-foreground">
          {output}
        </pre>
      </section>
    </main>
  );
}
