const stats = [
  { value: "6000+", label: "документов в RAG" },
  { value: "34", label: "видео транскрибировано" },
  { value: "35", label: "статей загружено" },
  { value: "7", label: "команд в Telegram боте" },
];

const features = [
  {
    title: "Голосовая модель",
    description:
      "Система анализирует 6000+ текстов Дмитрия Бескромного и воспроизводит его уникальный стиль: интонации, лексику, структуру мысли.",
  },
  {
    title: "RAG-пайплайн",
    description:
      "Все материалы — посты канала, статьи, расшифровки выступлений — индексированы в ChromaDB и доступны для контекстного поиска.",
  },
  {
    title: "Telegram-бот",
    description:
      "Команды /post, /rewrite, /comment, /idea и другие — генерация контента прямо в Telegram с обратной связью для улучшения качества.",
  },
  {
    title: "Петля обратной связи",
    description:
      "Каждый сгенерированный текст можно оценить: использовал, отредактировал, отклонил. Система учится на ваших решениях.",
  },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      {/* Hero */}
      <section className="flex flex-col items-center text-center py-20 animate-fade-in-up">
        <div className="inline-block rounded-full border border-[var(--color-accent)]/30 bg-[var(--color-accent)]/10 px-4 py-1.5 text-sm text-[var(--color-accent)] mb-6">
          Open-source AI-проект
        </div>
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight">
          <span className="text-[var(--color-accent)]">Бескромный</span>GPT
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-[var(--color-muted)]">
          Персональная голосовая модель и машина полуавтоматизации личного бренда
          Дмитрия Бескромного
        </p>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4 py-8">
        {stats.map((stat, i) => (
          <div
            key={stat.label}
            className={`animate-fade-in-up animate-delay-${(i + 1) * 100} rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-6 text-center transition hover:border-[var(--color-border-hover)]`}
          >
            <div className="text-3xl font-bold text-[var(--color-accent)]">
              {stat.value}
            </div>
            <div className="mt-2 text-sm text-[var(--color-muted)]">
              {stat.label}
            </div>
          </div>
        ))}
      </section>

      {/* What is this */}
      <section className="py-16 animate-fade-in-up animate-delay-300">
        <h2 className="text-2xl font-bold mb-4">Что это такое?</h2>
        <p className="text-[var(--color-muted)] leading-relaxed max-w-3xl">
          БескромныйGPT — это AI-система, которая изучила тысячи текстов медиаменеджера
          и предпринимателя Дмитрия Бескромного и научилась генерировать контент
          в его стиле. Система использует RAG (Retrieval-Augmented Generation)
          для поиска релевантного контекста и Claude для генерации текста.
          Весь проект создан методом vibe-coding с помощью AI — стоимость разработки
          стремится к нулю.
        </p>
      </section>

      {/* Features */}
      <section className="grid md:grid-cols-2 gap-6 py-8">
        {features.map((feature, i) => (
          <div
            key={feature.title}
            className={`animate-fade-in-up animate-delay-${((i % 4) + 1) * 100} rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-6 transition hover:border-[var(--color-border-hover)]`}
          >
            <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
            <p className="text-sm text-[var(--color-muted)] leading-relaxed">
              {feature.description}
            </p>
          </div>
        ))}
      </section>
    </main>
  );
}
