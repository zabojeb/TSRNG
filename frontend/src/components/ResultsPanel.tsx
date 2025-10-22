type AnalysisTest = {
  name: string;
  passed: boolean;
  p_value?: number;
  note?: string;
};

type ResultsPanelProps = {
  numbers: number[] | null;
  roundId: string | null;
  outputBits: number | null;
  analysis?: {
    bit_length: number;
    tests: AnalysisTest[];
    all_passed: boolean;
  };
  outputUrl?: string | null;
};

function formatNumberList(nums: number[]) {
  return nums.join(", ");
}

function ResultsPanel({ numbers, roundId, outputBits, analysis, outputUrl }: ResultsPanelProps) {
  if (!roundId) {
    return null;
  }
  return (
    <section className="card mt-8">
      <div className="flex flex-col gap-4">
        <header className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-brand-dark">Результаты</h2>
            <p className="text-sm text-slate-500">
              Round ID: <span className="font-mono text-xs">{roundId}</span>
            </p>
          </div>
          {outputUrl && (
            <a href={outputUrl} download className="cta-button text-sm">
              Скачать 1 000 000 бит
            </a>
          )}
        </header>

        {numbers && (
          <div className="rounded-xl bg-brand-light/80 p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Уникальные числа
            </h3>
            <p className="mt-2 font-semibold text-brand-dark">{formatNumberList(numbers)}</p>
          </div>
        )}

        {analysis && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                Анализ случайности
              </h3>
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  analysis.all_passed ? "bg-emerald-100 text-emerald-600" : "bg-red-100 text-red-600"
                }`}
              >
                {analysis.all_passed ? "Все тесты пройдены" : "Есть замечания"}
              </span>
            </div>
            <p className="text-sm text-slate-500">
              Проверено битов: {analysis.bit_length.toLocaleString()}{" "}
              {outputBits && analysis.bit_length < outputBits ? `(из ${outputBits.toLocaleString()})` : ""}
            </p>
            <ul className="grid gap-3 md:grid-cols-2">
              {analysis.tests.map((test) => (
                <li key={test.name} className="rounded-lg border border-slate-200 p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-brand-dark">{test.name}</span>
                    <span
                      className={`text-xs font-semibold ${
                        test.passed ? "text-emerald-500" : "text-red-500"
                      }`}
                    >
                      {test.passed ? "✅" : "⚠️"}
                    </span>
                  </div>
                  {test.p_value !== undefined && (
                    <p className="mt-1 text-xs text-slate-500">p-value: {test.p_value.toFixed(4)}</p>
                  )}
                  {test.note && <p className="mt-1 text-xs text-amber-600">{test.note}</p>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

export default ResultsPanel;
