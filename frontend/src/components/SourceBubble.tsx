type SourceBubbleProps = {
  name: string;
  description: string;
  active?: boolean;
  merged?: boolean;
};

function SourceBubble({ name, description, active = false, merged = false }: SourceBubbleProps) {
  return (
    <div
      className={`flex w-32 flex-col items-center gap-3 transition-all duration-700 ease-out ${
        merged ? "-translate-y-6 scale-110 opacity-80" : "opacity-100"
      }`}
    >
      <div
        className={`relative flex h-20 w-20 items-center justify-center rounded-full border-2 shadow-lg transition-all duration-500 ${
          active
            ? "border-brand-yellow bg-gradient-to-br from-brand-yellow/40 via-white to-white text-brand-dark"
            : "border-slate-200 bg-white text-slate-500"
        }`}
      >
        {active && <span className="absolute inset-0 -z-10 animate-ping rounded-full bg-brand-yellow/30" />}
        <span className="text-sm font-semibold">{name}</span>
      </div>
      <p className="text-center text-xs text-slate-500">{description}</p>
    </div>
  );
}

export default SourceBubble;
