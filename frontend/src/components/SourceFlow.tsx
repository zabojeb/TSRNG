import SourceBubble from "./SourceBubble";

type SourceFlowProps = {
  sources: { name: string; description: string }[];
  merge: boolean;
  stage: number;
};

const stageLabels = [
  { title: "Сбор", subtitle: "Получаем ответы от внешних источников" },
  { title: "Commit", subtitle: "Строим Merkle-дерево и фиксируем корень" },
  { title: "Beacon", subtitle: "Добавляем публичный seed и VDF" },
  { title: "Finalize", subtitle: "Выбираем листья и формируем поток битов" },
  { title: "Random Range", subtitle: "Детерминированно получаем числа" },
];

function SourceFlow({ sources, merge, stage }: SourceFlowProps) {
  const safeStage = Math.min(stageLabels.length - 1, Math.max(0, stage));
  return (
    <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-br from-white via-brand-light/40 to-white p-8 shadow-inner">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute -top-32 -left-32 h-64 w-64 rounded-full bg-brand-yellow/20 blur-3xl" />
        <div className="absolute -bottom-20 right-10 h-40 w-40 rounded-full bg-brand-dark/10 blur-3xl" />
      </div>
      <div className="relative flex flex-col items-center gap-10">
        <div className="flex flex-wrap items-center justify-center gap-6 md:gap-12">
          {sources.map((source) => (
            <SourceBubble key={source.name} name={source.name} description={source.description} active merged={merge} />
          ))}
        </div>
        <div className="relative flex w-full max-w-xl flex-col items-center gap-4">
          <div className="h-24 w-24 rounded-full border-4 border-brand-yellow/80 bg-white shadow-xl transition-all duration-700 ease-out">
            <div className="flex h-full w-full flex-col items-center justify-center gap-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Этап {safeStage + 1}/{stageLabels.length}
              </span>
              <span className="text-lg font-bold text-brand-dark">{stageLabels[safeStage].title}</span>
            </div>
          </div>
          <p className="max-w-md text-center text-sm text-slate-600">{stageLabels[safeStage].subtitle}</p>
          <div className="relative h-1 w-full overflow-hidden rounded-full bg-slate-200">
            <span
              className="absolute inset-y-0 left-0 rounded-full bg-brand-yellow transition-all duration-700 ease-out"
              style={{ width: `${((safeStage + 1) / stageLabels.length) * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default SourceFlow;
