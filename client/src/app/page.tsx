"use client";

import { useState, FormEvent, ChangeEvent } from "react";
import useSampleQuery from "@/hooks/useSampleQuery";

export default function Home() {
  const [query, setQuery] = useState<string>("");
  const [submittedQuery, setSubmittedQuery] = useState<string>("");
  const { data, error, isFetching } = useSampleQuery(submittedQuery);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmittedQuery(query.trim());
  }

  let output = "결과가 여기에 표시됩니다.";

  if (isFetching) {
    output = "요청 중...";
  } else if (error) {
    output = JSON.stringify({ error: error.message }, null, 2);
  } else if (data) {
    output = JSON.stringify(data, null, 2);
  }

  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-6 py-10">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="text-sm font-medium text-slate-700">Query</label>
        <input
          type="text"
          value={query}
          onChange={(event: ChangeEvent<HTMLInputElement>) => setQuery(event.target.value)}
          placeholder="검색할 쿼리를 입력하세요"
          className="w-full rounded-md border border-slate-200 px-4 py-2 text-sm outline-none focus:border-slate-400"
        />
        <button
          type="submit"
          className="inline-flex h-10 items-center justify-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white disabled:opacity-60"
          disabled={isFetching}
        >
          {isFetching ? "요청 중..." : "검색"}
        </button>
      </form>

      <section className="mt-8">
        <div className="mb-2 text-sm font-medium text-slate-700">Response</div>
        <pre className="min-h-[200px] whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-sm text-slate-800">
          {output}
        </pre>
      </section>
    </main>
  );
}
