import { useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchRounds, type RoundSummary } from "../api/tsrng";
import pipelineImg from "../assets/pipeline_placeholder.svg";
import merkleImg from "../assets/merkle_placeholder.svg";
import sourcesImg from "../assets/sources_placeholder.svg";

const stageLabels: Record<string, string> = {
  committed: "Собранные листья",
  beaconed: "Beacon установлен",
  finalized: "Раунд завершён",
};

const stageDescriptions: Record<string, string> = {
  committed: "Пакеты энтропии находятся в хранилище, Merkle-дерево можно пересчитать самостоятельно.",
  beaconed: "Beacon опубликован, VDF рассчитан. Готовимся к детерминированному отбору листьев.",
  finalized:
    "Финальный поток сформирован, артефакты, доказательства и миллион бит доступны для скачивания и аудита.",
};

const trustPillars = [
  {
    icon: "🧭",
    title: "Прозрачный путь данных",
    description:
      "Каждый шаг — от сбора энтропии до публикации результатов — фиксируется в manifest.json и доступен в API без авторизации.",
  },
  {
    icon: "🪪",
    title: "Криптографическая доказуемость",
    description:
      "Merkle-деревья, VDF и HKDF обеспечивают, что ни один бит нельзя подменить, не оставив криптографический след.",
  },
  {
    icon: "📊",
    title: "Постоянный аудит",
    description:
      "История анализов, экспорт 1 000 000 бит и сравнения с эталонами позволяют проходить проверку NIST STS и Dieharder.",
  },
];

function Step({ title, description, number }: { title: string; description: string; number: number }) {
  return (
    <div className="relative flex flex-col gap-3 rounded-3xl border border-slate-200 bg-gradient-to-br from-white via-brand-light/60 to-white p-6 shadow-lg">
      <span className="absolute -top-6 left-6 flex h-12 w-12 items-center justify-center rounded-full bg-brand-yellow text-xl font-semibold text-brand-dark shadow-lg">
        {number}
      </span>
      <h3 className="mt-6 text-xl font-semibold text-brand-dark">{title}</h3>
      <p className="text-sm text-slate-600">{description}</p>
    </div>
  );
}

function HowItWorksPage() {
  const [latestRound, setLatestRound] = useState<RoundSummary | null>(null);
  const [roundCount, setRoundCount] = useState(0);
  const [loadingStats, setLoadingStats] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoadingStats(true);
        setStatsError(null);
        const items = await fetchRounds(200);
        setRoundCount(items.length);
        setLatestRound(items[0] ?? null);
      } catch (err: any) {
        setStatsError(err?.message || "Не удалось загрузить статистику раундов.");
      } finally {
        setLoadingStats(false);
      }
    }
    load();
  }, []);

  const streamsCount = useMemo(
    () => (latestRound?.streams ? Object.keys(latestRound.streams).length : 0),
    [latestRound],
  );

  const stageLabel = latestRound ? stageLabels[latestRound.stage] || latestRound.stage : "—";
  const stageNarrative = latestRound ? stageDescriptions[latestRound.stage] || "" : "";
  const latestBits = latestRound?.output_bits ? latestRound.output_bits.toLocaleString() : "—";
  const latestRoundLabel =
    latestRound?.round_label || (latestRound?.round_id ? `Раунд ${latestRound.round_id.slice(0, 6)}` : "—");

  return (
    <section className="page-container space-y-12">
      <header className="space-y-4 text-center">
        <h1 className="text-3xl font-semibold text-brand-dark md:text-4xl">
          Как RandomTrust делает случайность понятной
        </h1>
        <p className="text-slate-600 md:text-lg">
          Мы не просим верить на слово — мы показываем путь каждого бита. Ознакомьтесь с живой статистикой, ключевыми
          принципами и визуализацией конвейера.
        </p>
      </header>

      {statsError && <p className="text-center text-sm text-red-500">{statsError}</p>}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StoryStat
          icon="🎯"
          label="Проведено раундов"
          value={loadingStats ? "…" : roundCount.toLocaleString()}
          caption="Каждый раунд сохраняется вместе с артефактами и анализом."
          loading={loadingStats}
        />
        <StoryStat
          icon="🛰️"
          label="Статус последнего раунда"
          value={loadingStats ? "…" : stageLabel}
          caption={stageNarrative || "История этапов доступна в разделе «История раундов»."}
          loading={loadingStats}
        />
        <StoryStat
          icon="🔗"
          label="Подключено потоков энтропии"
          value={loadingStats ? "…" : streamsCount.toString()}
          caption="Физические, сетевые и алгоритмические источники работают параллельно."
          loading={loadingStats}
        />
        <StoryStat
          icon="📦"
          label="Размер итоговой последовательности"
          value={loadingStats ? "…" : `${latestBits} бит`}
          caption="Готовый файл из 1 000 000 бит доступен в output.txt."
          loading={loadingStats}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-brand-dark">Три столпа доверия RandomTrust</h2>
          <p className="mt-2 text-sm text-slate-600">
            Наш конвейер спроектирован так, чтобы любой участник — оператор, аудитор или регулятор — мог получить
            доказательства корректности без специальных инструментов.
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {trustPillars.map((pillar) => (
              <StoryPillar key={pillar.title} icon={pillar.icon} title={pillar.title} description={pillar.description} />
            ))}
          </div>
        </div>

        <VideoTeaser
          loading={loadingStats}
          latestRoundLabel={latestRoundLabel}
          stageLabel={stageLabel}
          stageNarrative={stageNarrative}
        />
      </div>

      <div className="grid gap-12 md:grid-cols-2">
        <div className="flex flex-col gap-6">
          <img src={sourcesImg} alt="Каналы энтропии" className="w-full rounded-3xl border border-slate-200 shadow" />
          <Step
            number={1}
            title="Сбор и фиксация энтропии"
            description="Маяки (drand, NIST), рыночные котировки, погодные параметры, текстовые события и изображения собираются асинхронно. Каждый ответ хэшируется SHA3-512, сохраняется вместе с метаданными и публикуется в разделе прозрачности."
          />
          <Step
            number={2}
            title="Commit: Merkle-дерево"
            description="Все листья объединяются в Merkle-дерево (TSRNG/commit). Корень и индекс потоков записываются в manifest.json. Внешний сид ещё не добавлен — репликация шага возможна любым аудитором."
          />
          <Step
            number={3}
            title="Beacon + VDF"
            description="Оператор публикует seed (например, из drand). Из него выводится простое число, запускается VDF (SLOTH). Результат фиксируется в vdf/proof.json. Любой желающий может повторить вычисления."
          />
          <Step
            number={4}
            title="Finalize и детерминированный отбор"
            description="Корень Merkle и сид используются для детерминированного выбора листьев. Биты агрегируются, проходят через HKDF и образуют финальный поток. Готовятся proofs, архив и текстовый файл из 1 000 000 бит."
          />
          <Step
            number={5}
            title="Статистика и heavy tests"
            description="Автоматически запускаются базовые тесты (monobit, runs, блоки, байты). При необходимости можно инициировать Dieharder/TestU01. Каждый запуск фиксируется в истории, отчёты доступны по API."
          />
        </div>
        <div className="flex flex-col gap-6">
          <div className="gradient-card">
            <h2 className="text-lg font-semibold text-brand-dark">Визуализация конвейера</h2>
            <div className="mt-6 space-y-6">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:gap-6">
                <div className="flex flex-1 items-center justify-center gap-4">
                  {["Entropy", "Commit", "Beacon", "Finalize", "Range"].map((label, idx) => (
                    <div key={label} className="flex flex-col items-center text-xs font-semibold text-slate-500">
                      <div className="h-10 w-10 rounded-full border border-brand-yellow/60 bg-brand-yellow/20 text-brand-dark shadow">
                        <div className="flex h-full w-full items-center justify-center">{idx + 1}</div>
                      </div>
                      <span className="mt-1 uppercase tracking-wide">{label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <p className="text-sm text-slate-600">
                Визуальная лента на странице «Генерация» подсвечивает активные источники и прогресс pipeline — удобно для
                демонстраций и внутренних отчётов.
              </p>
            </div>
            <img src={pipelineImg} alt="Обзор конвейера" className="mt-6 w-full rounded-3xl border border-slate-200 shadow" />
          </div>
          <div className="rounded-3xl bg-brand-dark/95 p-6 text-brand-light shadow-lg">
            <h2 className="text-lg font-semibold text-brand-yellow">Ключевые ссылки API</h2>
            <ul className="mt-4 space-y-2 text-sm">
              <li>
                <code>/rounds/&lt;id&gt;/manifest</code> — полное описание раунда, включая источники и параметры VDF.
              </li>
              <li>
                <code>/rounds/&lt;id&gt;/raw/summary</code> — сырые данные и хэши.
              </li>
              <li>
                <code>/rounds/&lt;id&gt;/output.txt</code> — 1 000 000 бит для независимого тестирования.
              </li>
              <li>
                <code>/rounds/&lt;id&gt;/analysis/history</code> — журнал всех проведённых проверок.
              </li>
            </ul>
          </div>
          <div className="gradient-card space-y-6">
            <h2 className="text-lg font-semibold text-brand-dark">Для регуляторов и аудиторов</h2>
            <p className="mt-3 text-sm text-slate-600">
              Полный пакет (artifact.zip) содержит выборку листьев, доказательства, seed и VDF, а также текстовый файл
              с битами. Интеграцию с TestU01/NIST STS можно выполнять, используя наш текстовый файл и зафиксированные
              параметры. Вся информация доступна по публичным API без дополнительной авторизации.
            </p>
            <img src={merkleImg} alt="Merkle proof" className="w-full rounded-3xl border border-slate-200 shadow" />
          </div>
        </div>
      </div>
    </section>
  );
}

type StoryStatProps = {
  icon?: string;
  label: string;
  value: ReactNode;
  caption?: ReactNode;
  loading?: boolean;
};

function StoryStat({ icon, label, value, caption, loading }: StoryStatProps) {
  return (
    <div
      className={`rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition ${
        loading ? "animate-pulse" : ""
      }`}
    >
      <div className="flex items-center gap-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
        {icon && (
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-light/80 text-lg text-brand-dark shadow">
            {icon}
          </span>
        )}
        {label}
      </div>
      <div className="mt-3 text-2xl font-semibold text-brand-dark">{value}</div>
      {caption && <p className="mt-2 text-xs text-slate-500">{caption}</p>}
    </div>
  );
}

type StoryPillarProps = {
  icon: string;
  title: string;
  description: string;
};

function StoryPillar({ icon, title, description }: StoryPillarProps) {
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-slate-100 bg-brand-light/50 p-4 text-sm text-slate-600 shadow-sm">
      <span className="text-2xl">{icon}</span>
      <h3 className="text-base font-semibold text-brand-dark">{title}</h3>
      <p>{description}</p>
    </div>
  );
}

type VideoTeaserProps = {
  loading: boolean;
  latestRoundLabel: string;
  stageLabel: string;
  stageNarrative: string;
};

function VideoTeaser({ loading, latestRoundLabel, stageLabel, stageNarrative }: VideoTeaserProps) {
  return (
    <div className="flex flex-col justify-between gap-4 rounded-3xl bg-brand-dark/95 p-6 text-brand-light shadow-lg">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-brand-yellow">Видео-демо (скоро)</h2>
        <p className="text-sm text-brand-light/90">
          Готовим 7-минутный скринкаст, который покажет работу системы: от подключения источников до экспорта артефактов
          и запуска Dieharder. Подпишитесь, чтобы не пропустить релиз.
        </p>
        <div className="rounded-2xl border border-brand-yellow/30 bg-brand-dark/60 p-4 text-xs uppercase tracking-wide text-brand-light/80">
          <p className="text-brand-yellow">Текущий раунд: {loading ? "…" : latestRoundLabel}</p>
          <p className="mt-1 text-brand-light">Статус: {loading ? "…" : stageLabel}</p>
          {stageNarrative && <p className="mt-1 text-brand-light/70 normal-case">{stageNarrative}</p>}
        </div>
      </div>
      <div className="relative mt-3 flex aspect-video w-full items-center justify-center overflow-hidden rounded-2xl border border-brand-yellow/30 bg-black/40">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-yellow/10 via-transparent to-brand-yellow/20" />
        <button
          type="button"
          className="flex items-center gap-2 rounded-full bg-brand-yellow px-4 py-2 text-xs font-semibold uppercase tracking-wide text-brand-dark shadow-lg transition hover:-translate-y-0.5 hover:shadow-xl"
          disabled
        >
          ▶ Скринкаст появится после записи
        </button>
      </div>
    </div>
  );
}

export default HowItWorksPage;
