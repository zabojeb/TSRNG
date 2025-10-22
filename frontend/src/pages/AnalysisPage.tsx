import { FormEvent, useState } from "react";
import { analyzeSequence, uploadSequence } from "../api/tsrng";

type AnalysisResult = {
  bit_length: number;
  ones: number;
  zeros: number;
  proportion_ones: number;
  entropy_per_byte?: number;
  tests: { name: string; passed: boolean; p_value?: number; note?: string }[];
  all_passed: boolean;
  source: Record<string, any>;
};

function AnalysisPage() {
  const [mode, setMode] = useState<"text" | "file">("text");
  const [textInput, setTextInput] = useState("");
  const [limitBits, setLimitBits] = useState<number | undefined>(undefined);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      let response: AnalysisResult;
      if (mode === "file") {
        if (!file) {
          throw new Error("Приложите файл для анализа.");
        }
        response = await uploadSequence(file, limitBits);
      } else {
        const trimmed = textInput.trim();
        if (!trimmed) {
          throw new Error("Введите последовательность.");
        }
        const payload: any = {};
        if (limitBits) {
          payload.limit_bits = limitBits;
        }

        const tokens = trimmed.split(/[\s,;,]+/).filter(Boolean);
        const allNumericTokens = tokens.length > 1 && tokens.every((token) => /^\d+$/.test(token));

        if (/^[01\s]+$/.test(trimmed)) {
          payload.data_bits = trimmed.replace(/\s+/g, "");
        } else if (allNumericTokens) {
          const numbers = tokens.map((token) => Number(token));
          if (numbers.every((n) => n === 0 || n === 1)) {
            payload.data_bits = numbers.join("");
          } else if (numbers.every((n) => n >= 0 && n <= 255)) {
            payload.data_numbers = numbers;
          } else {
            throw new Error("Числовой ввод поддерживает значения 0/1 или 0..255.");
          }
        } else if (/^[0-9a-fA-F\s]+$/.test(trimmed)) {
          const hex = trimmed.replace(/\s+/g, "");
          if (hex.length % 2 !== 0) {
            throw new Error("Hex-строка должна содержать чётное число символов.");
          }
          payload.data_hex = hex;
        } else {
          payload.data_base64 = trimmed.replace(/\s+/g, "");
        }

        response = await analyzeSequence(payload);
      }
      setResult(response);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Ошибка анализа");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-container space-y-10">
      <header className="space-y-3 text-center">
        <h1 className="text-3xl font-semibold text-brand-dark md:text-4xl">Анализ случайности</h1>
        <p className="text-slate-600">
          Загрузите результат стороннего генератора или вставьте последовательность — система автоматически запустит
          набор тестов (monobit, runs, block frequency, распределение байтов). История запусков сохраняется.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="card space-y-6">
        <div className="flex flex-wrap gap-4">
          <button
            type="button"
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              mode === "text" ? "bg-brand-yellow text-brand-dark" : "bg-slate-100 text-slate-500"
            }`}
            onClick={() => setMode("text")}
          >
            Текстовый ввод
          </button>
          <button
            type="button"
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              mode === "file" ? "bg-brand-yellow text-brand-dark" : "bg-slate-100 text-slate-500"
            }`}
            onClick={() => setMode("file")}
          >
            Загрузка файла
          </button>
        </div>

        {mode === "text" ? (
          <div className="space-y-2">
            <label className="text-sm font-medium text-brand-dark">
              Последовательность (поддерживаются 0/1, hex, base64)
            </label>
            <textarea
              className="h-40 w-full rounded-xl border border-slate-200 px-3 py-2 font-mono text-sm focus:border-brand-yellow focus:outline-none"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Например: 0 1 1 0 …"
            />
          </div>
        ) : (
          <div className="space-y-2">
            <label className="text-sm font-medium text-brand-dark">Файл (binary/текст)</label>
            <input
              type="file"
              accept=".bin,.txt,.dat,.raw"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="text-sm text-slate-600"
            />
            {file && (
              <p className="text-xs text-slate-500">
                {file.name} — {(file.size / 1024).toFixed(1)} KB ({(file.size * 8).toLocaleString()} бит)
              </p>
            )}
          </div>
        )}

        <div className="flex flex-col gap-2 text-sm">
          <label className="font-medium text-brand-dark">
            Ограничение на число анализируемых бит (опционально)
          </label>
          <input
            type="number"
            min={8}
            className="max-w-xs rounded-lg border border-slate-200 px-3 py-2 focus:border-brand-yellow focus:outline-none"
            value={limitBits ?? ""}
            onChange={(e) => setLimitBits(e.target.value ? Number(e.target.value) : undefined)}
          />
        </div>

        <button type="submit" className="cta-button" disabled={loading}>
          {loading ? "Анализируем…" : "Запустить анализ"}
        </button>
        {error && <p className="text-sm text-red-500">{error}</p>}
      </form>

      {result && (
        <section className="card space-y-4">
          <header className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
            <h2 className="text-lg font-semibold text-brand-dark">Результаты тестов</h2>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                result.all_passed ? "bg-emerald-100 text-emerald-600" : "bg-red-100 text-red-600"
              }`}
            >
              {result.all_passed ? "Все тесты пройдены" : "Есть замечания"}
            </span>
          </header>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl bg-brand-light/80 p-4">
              <h3 className="text-xs font-semibold uppercase text-slate-500">Статистика</h3>
              <ul className="mt-2 space-y-1 text-sm text-brand-dark">
                <li>Длина: {result.bit_length.toLocaleString()} бит</li>
                <li>Единиц: {result.ones.toLocaleString()}</li>
                <li>Нулей: {result.zeros.toLocaleString()}</li>
                <li>Доля единиц: {result.proportion_ones.toFixed(4)}</li>
                {result.entropy_per_byte !== undefined && (
                  <li>Энтропия/байт: {result.entropy_per_byte.toFixed(3)} бит</li>
                )}
              </ul>
            </div>
            <div className="rounded-xl bg-white p-4">
              <h3 className="text-xs font-semibold uppercase text-slate-500">Источник</h3>
              <pre className="mt-2 max-h-36 overflow-auto whitespace-pre-wrap text-xs text-slate-600">
                {JSON.stringify(result.source, null, 2)}
              </pre>
            </div>
          </div>
          <ul className="grid gap-3 md:grid-cols-2">
            {result.tests.map((test) => (
              <li key={test.name} className="rounded-lg border border-slate-200 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-brand-dark">{test.name}</span>
                  <span className={`text-xs font-semibold ${test.passed ? "text-emerald-500" : "text-red-500"}`}>
                    {test.passed ? "✅" : "⚠️"}
                  </span>
                </div>
                {(() => {
                  const pValue = test.p_value;
                  if (pValue === null || pValue === undefined) {
                    return null;
                  }
                  if (typeof pValue === "number" && Number.isFinite(pValue)) {
                    return (
                      <p className="mt-1 text-xs text-slate-500">p-value: {pValue.toFixed(4)}</p>
                    );
                  }
                  return <p className="mt-1 text-xs text-slate-500">p-value: {String(pValue)}</p>;
                })()}
                {test.note && <p className="mt-1 text-xs text-amber-600">{test.note}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}

export default AnalysisPage;
