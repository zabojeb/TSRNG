import { useState, useMemo, useEffect } from "react";
import SourceFlow from "../components/SourceFlow";
import ResultsPanel from "../components/ResultsPanel";
import pipelineImg from "../assets/pipeline_placeholder.svg";
import sourcesImg from "../assets/sources_placeholder.svg";
import merkleImg from "../assets/merkle_placeholder.svg";
import {
  collectAndCommit,
  postBeacon,
  finalizeRound,
  generateRange,
  fetchOutputText,
  analyzeRound,
  runHeavyTest,
} from "../api/tsrng";

const defaultCounts = {
  beacons: 8,
  quotes: 32,
  weather: 16,
  text: 16,
  images: 8,
};

const sources = [
  { name: "Beacons", description: "drand, NIST и доп. маяки" },
  { name: "Quotes", description: "Крипто/биржевые котировки" },
  { name: "Weather", description: "Open-Meteo по нескольким городам" },
  { name: "Text", description: "Wikipedia и GitHub события" },
  { name: "Images", description: "Подбор статичных изображений" },
];

function generateSeedHex(bytes = 32) {
  const array = new Uint8Array(bytes);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

function GeneratePage() {
  const [counts, setCounts] = useState(defaultCounts);
  const [rangeStart, setRangeStart] = useState(1);
  const [rangeEnd, setRangeEnd] = useState(42);
  const [rangeCount, setRangeCount] = useState(6);
  const [outputBits, setOutputBits] = useState(4096);
  const [includeMillionBits, setIncludeMillionBits] = useState(true);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [roundId, setRoundId] = useState<string | null>(null);
  const [numbers, setNumbers] = useState<number[] | null>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [outputUrl, setOutputUrl] = useState<string | null>(null);
  const [seedHex, setSeedHex] = useState<string | null>(null);
  const [mergeVisual, setMergeVisual] = useState(false);
  const [stage, setStage] = useState(0);
  const [heavyResult, setHeavyResult] = useState<any>(null);

  useEffect(() => {
    return () => {
      if (outputUrl) {
        URL.revokeObjectURL(outputUrl);
      }
    };
  }, [outputUrl]);

  const canGenerate = useMemo(() => {
    return rangeEnd >= rangeStart && rangeCount > 0 && rangeCount <= rangeEnd - rangeStart + 1;
  }, [rangeStart, rangeEnd, rangeCount]);

  async function handleGenerate() {
    if (!canGenerate) {
      setError("Проверьте диапазон и количество уникальных чисел.");
      return;
    }
    setLoading(true);
    setMergeVisual(true);
    setProgress("Сбор источников…");
    setError(null);
    setNumbers(null);
    setAnalysis(null);
    setHeavyResult(null);
    setRoundId(null);
    setStage(0);
    if (outputUrl) {
      URL.revokeObjectURL(outputUrl);
      setOutputUrl(null);
    }

    try {
      const commitPayload = {
        round_label: "frontend",
        counts,
        persist_raw: true,
      };
      const commit = await collectAndCommit(commitPayload);
      const newRoundId = commit.round_id;
      setRoundId(newRoundId);

      setStage(0);

      const seed = generateSeedHex();
      setSeedHex(seed);
      setProgress("Установка маяка…");
      setStage(1);
      await postBeacon(newRoundId, { S_hex: seed, vdf_T: 50, modulus_bits: 512 });

      const bitsToRequest = includeMillionBits ? 1_000_000 : outputBits;
      setProgress(`Финализация раунда (${bitsToRequest.toLocaleString()} бит)…`);
      setStage(2);
      const finalize = await finalizeRound(newRoundId, { output_bits: bitsToRequest });
      if (finalize?.analysis) {
        setAnalysis(finalize.analysis);
      }

      setProgress("Определение случайных чисел…");
      setStage(3);
      const rangeResponse = await generateRange(newRoundId, {
        start: rangeStart,
        end: rangeEnd,
        count: rangeCount,
        domain: "frontend",
        context: "ui",
      });
      setNumbers(rangeResponse.numbers);

      if (includeMillionBits) {
        setProgress("Подготовка текстового файла 1 000 000 бит…");
        const blob = await fetchOutputText(newRoundId);
        const url = URL.createObjectURL(blob);
        setOutputUrl(url);
      }

      setProgress("Анализ случайности…");
      setStage(4);
      const analysisResult = await analyzeRound(newRoundId, bitsToRequest);
      setAnalysis(analysisResult);

      setProgress("Запуск Dieharder…");
      const heavy = await runHeavyTest(newRoundId);
      setHeavyResult(heavy);

      setProgress("Готово!");
      setTimeout(() => setMergeVisual(false), 800);
    } catch (err: any) {
      console.error(err);
      setError(err?.response?.data?.detail || err.message || "Неизвестная ошибка");
      setMergeVisual(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-container space-y-10">
      <header className="space-y-3 text-center">
        <h1 className="text-3xl font-semibold text-brand-dark md:text-4xl">Генерация тиража</h1>
        <p className="text-slate-600">
          Все источники энтропии собираются, фиксируются в Merkle-дереве, смешиваются с публичным сидом и
          воспроизводимо превращаются в числа. Настройте диапазон, количество и объём выходных битов.
        </p>
      </header>

      <section className="card space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-brand-dark">Визуализация конвейера</h2>
          <p className="mt-1 text-sm text-slate-500">
            Источники собираются параллельно, затем через commit, beacon и finalize преобразуются в итоговый поток.
          </p>
        </div>
        <SourceFlow sources={sources} merge={mergeVisual && loading} stage={stage} />
        <div className="grid gap-4 md:grid-cols-2">
          <img
            src={pipelineImg}
            alt="Обзор конвейера"
            className="w-full rounded-3xl border border-slate-200 shadow"
          />
          <div className="flex flex-col justify-center gap-3 text-sm text-slate-600">
            <p>
              Каждый источник фиксируется с метаданными и хэшами. Merkle-дерево делает данные неизменяемыми, а внешние
              beacon и VDF добавляют непредсказуемость.
            </p>
            <p>
              После finalize поток битов проходит через HKDF — его можно скачать в текстовом виде и проверять с помощью
              внешних тестов.
            </p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <img
            src={sourcesImg}
            alt="Источники энтропии"
            className="w-full rounded-3xl border border-slate-200 shadow"
          />
          <img
            src={merkleImg}
            alt="Merkle и доказательства"
            className="w-full rounded-3xl border border-slate-200 shadow"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {Object.entries(counts).map(([key, value]) => (
            <label key={key} className="flex flex-col gap-2 text-sm">
              <span className="font-medium text-brand-dark">
                {key === "beacons"
                  ? "Маяки"
                  : key === "quotes"
                  ? "Котировки"
                  : key === "weather"
                  ? "Погода"
                  : key === "text"
                  ? "Текстовые фиды"
                  : "Изображения"}
              </span>
              <input
                type="number"
                min={1}
                className="rounded-lg border border-slate-200 px-3 py-2 shadow-sm focus:border-brand-yellow focus:outline-none"
                value={value}
                onChange={(e) => setCounts((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
              />
            </label>
          ))}
        </div>
      </section>

      <section className="card grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-brand-dark">Настройки диапазона</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="flex flex-col text-sm">
              <span className="font-medium text-brand-dark">Начало (a)</span>
              <input
                type="number"
                className="rounded-lg border border-slate-200 px-3 py-2 focus:border-brand-yellow focus:outline-none"
                value={rangeStart}
                onChange={(e) => setRangeStart(Number(e.target.value))}
              />
            </label>
            <label className="flex flex-col text-sm">
              <span className="font-medium text-brand-dark">Конец (b)</span>
              <input
                type="number"
                className="rounded-lg border border-slate-200 px-3 py-2 focus:border-brand-yellow focus:outline-none"
                value={rangeEnd}
                onChange={(e) => setRangeEnd(Number(e.target.value))}
              />
            </label>
            <label className="flex flex-col text-sm">
              <span className="font-medium text-brand-dark">Кол-во чисел</span>
              <input
                type="number"
                min={1}
                className="rounded-lg border border-slate-200 px-3 py-2 focus:border-brand-yellow focus:outline-none"
                value={rangeCount}
                onChange={(e) => setRangeCount(Number(e.target.value))}
              />
            </label>
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-brand-dark">Настройки выходных битов</h2>
          <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-brand-light/60 px-4 py-3 text-sm">
            <input
              type="checkbox"
              checked={includeMillionBits}
              onChange={(e) => setIncludeMillionBits(e.target.checked)}
              className="h-4 w-4 accent-brand-yellow"
            />
            <span>Сгенерировать текстовый файл из ровно 1 000 000 бит и запустить анализ</span>
          </label>
          <div className="flex flex-col gap-2 text-sm">
            <span className="font-medium text-brand-dark">Количество бит (если не миллион)</span>
            <input
              type="number"
              min={512}
              step={256}
              className="max-w-xs rounded-lg border border-slate-200 px-3 py-2 focus:border-brand-yellow focus:outline-none"
              disabled={includeMillionBits}
              value={outputBits}
              onChange={(e) => setOutputBits(Number(e.target.value))}
            />
          </div>
        </div>
      </section>

      <section className="flex flex-col items-center gap-4">
        <button
          type="button"
          className="cta-button text-lg"
          disabled={loading}
          onClick={handleGenerate}
        >
          {loading ? "Идёт генерация…" : "Запустить генерацию"}
        </button>
        {progress && <p className="text-sm text-slate-500">{progress}</p>}
        {seedHex && roundId && (
          <p className="rounded-full bg-white px-4 py-2 text-xs text-slate-500">
            Использованный seed (hex): <span className="font-mono">{seedHex.slice(0, 16)}…</span>
          </p>
        )}
        {error && <p className="text-sm text-red-500">{error}</p>}
      </section>

      <ResultsPanel
        numbers={numbers}
        roundId={roundId}
        outputBits={includeMillionBits ? 1_000_000 : outputBits}
        analysis={analysis}
        outputUrl={outputUrl}
      />

      {heavyResult && (
        <section className="card">
          <h2 className="text-lg font-semibold text-brand-dark">Dieharder</h2>
          <p className="text-sm text-slate-500">
            Статус:{" "}
            <span className={heavyResult.status === "completed" ? "text-emerald-500" : "text-red-500"}>
              {heavyResult.status}
            </span>
          </p>
          {heavyResult.result?.stdout && (
            <pre className="mt-4 max-h-64 overflow-auto rounded-xl bg-slate-900 p-4 text-xs text-slate-100">
              {heavyResult.result.stdout}
            </pre>
          )}
          {heavyResult.error && <p className="mt-2 text-sm text-red-500">{heavyResult.error}</p>}
        </section>
      )}
    </section>
  );
}

export default GeneratePage;
