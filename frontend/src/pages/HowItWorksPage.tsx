import pipelineImg from "../assets/pipeline_placeholder.svg";
import merkleImg from "../assets/merkle_placeholder.svg";
import sourcesImg from "../assets/sources_placeholder.svg";

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
  return (
    <section className="page-container space-y-12">
      <header className="space-y-3 text-center">
        <h1 className="text-3xl font-semibold text-brand-dark md:text-4xl">Как устроен RandomTrust TSRNG</h1>
        <p className="text-slate-600">
          Весь цикл генерации прозрачный: каждый шаг фиксируется, хэшируется и воспроизводимо проверяется. Ниже —
          визуализация конвейера и ссылки на артефакты для самостоятельного аудита.
        </p>
      </header>

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
            title="Статистика + Dieharder"
            description="Автоматически запускаются базовые тесты (monobit, runs, блоки, байты) и Dieharder. Каждый запуск фиксируется в истории, отчёты доступны по API."
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
                На странице «Генерация» источники визуально объединяются в центральный узел, отражая процесс смешивания
                энтропии. Полоса прогресса отображает текущее состояние pipeline.
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

export default HowItWorksPage;
