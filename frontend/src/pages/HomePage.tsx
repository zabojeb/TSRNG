import { Link } from "react-router-dom";

function HomePage() {
  const heroSteps = ["Entropy", "Merkle", "VDF", "HKDF", "Analysis"];

  return (
    <section className="page-container flex flex-col items-center gap-16 text-center">
      <div className="relative flex w-full flex-col items-center gap-10">
        <div className="absolute -top-32 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-brand-yellow/20 blur-3xl" />
        <div className="max-w-2xl space-y-6">
          <p className="rounded-full bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] text-brand-yellow shadow-sm">
            RandomTrust
          </p>
          <h1 className="text-4xl font-semibold text-brand-dark md:text-5xl">
            Прозрачный генератор случайных чисел для лотерей и аудита
          </h1>
          <p className="text-lg text-slate-600">
            TSRNG объединяет несколько источников реальной энтропии, фиксирует доказательства, генерирует тиражи и
            автоматически запускает статистические проверки. Вся цепочка — от сбора данных до итоговой последовательности —
            доступна для независимой проверки.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link to="/generate" className="cta-button">
              Генерировать тираж
            </Link>
            <Link to="/analysis" className="inline-flex items-center gap-2 text-sm font-semibold text-brand-dark">
              Проверить свою последовательность →
            </Link>
          </div>
        </div>

        <div className="gradient-card w-full max-w-4xl">
          <h2 className="text-lg font-semibold text-brand-dark">Полная прозрачность конвейера</h2>
          <div className="mt-6 grid gap-4 text-sm text-slate-600 md:grid-cols-5">
            {heroSteps.map((label, idx) => (
              <div key={label} className="flex flex-col items-center gap-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-yellow/30 text-brand-dark">
                  {idx + 1}
                </div>
                <span className="font-semibold text-brand-dark">{label}</span>
                <p className="text-xs text-slate-500">
                  {idx === 0
                    ? "Сбор из независимых источников"
                    : idx === 1
                    ? "Commit в Merkle-дерево"
                    : idx === 2
                    ? "Публичный seed и VDF"
                    : idx === 3
                    ? "Детерминированное смешивание"
                    : "Автоматические тесты"}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid w-full gap-6 sm:grid-cols-3">
        {[
          {
            title: "Мульти-энтропия",
            description: "Независимые источники: маяки, котировки, погода, текстовые и медийные фиды.",
          },
          {
            title: "Доказуемость",
            description:
              "Merkle-пруфы, VDF и полный архив необработанных данных доступны публично для аудита.",
          },
          {
            title: "Глубокий анализ",
            description:
              "Встроенные тесты, интеграция с Dieharder и история всех запусков обеспечивают воспроизводимость.",
          },
        ].map((card) => (
          <div key={card.title} className="gradient-card text-left">
            <h3 className="text-lg font-semibold text-brand-dark">{card.title}</h3>
            <p className="mt-2 text-sm text-slate-600">{card.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default HomePage;
