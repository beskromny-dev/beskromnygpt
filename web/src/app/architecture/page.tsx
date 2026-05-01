function Arrow({ direction = "down" }: { direction?: "down" | "right" | "up" }) {
  const arrows = {
    down: "M12 5v14m0 0l-4-4m4 4l4-4",
    right: "M5 12h14m0 0l-4-4m4 4l-4 4",
    up: "M12 19V5m0 0L8 9m4-4l4 4",
  };
  return (
    <div className="flex items-center justify-center py-2">
      <svg
        className="h-8 w-8 text-[var(--color-accent)]"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d={arrows[direction]} />
      </svg>
    </div>
  );
}

function Block({
  title,
  subtitle,
  accent = false,
  items,
}: {
  title: string;
  subtitle?: string;
  accent?: boolean;
  items?: string[];
}) {
  return (
    <div
      className={`rounded-xl border p-5 text-center transition ${
        accent
          ? "border-[var(--color-accent)]/50 bg-[var(--color-accent)]/10"
          : "border-[var(--color-border)] bg-[var(--color-card)]"
      }`}
    >
      <div className={`font-semibold text-lg ${accent ? "text-[var(--color-accent)]" : ""}`}>
        {title}
      </div>
      {subtitle && (
        <div className="text-xs text-[var(--color-muted)] mt-1">{subtitle}</div>
      )}
      {items && (
        <div className="mt-3 flex flex-wrap justify-center gap-2">
          {items.map((item) => (
            <span
              key={item}
              className="rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] px-2.5 py-0.5 text-xs text-[var(--color-muted)]"
            >
              {item}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ArchitecturePage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-16">
      <div className="animate-fade-in-up">
        <h1 className="text-3xl font-bold mb-2">Архитектура системы</h1>
        <p className="text-[var(--color-muted)] mb-12">
          Как устроен БескромныйGPT — от исходных данных до генерации контента с обратной связью.
        </p>
      </div>

      {/* Main pipeline */}
      <section className="animate-fade-in-up animate-delay-100">
        <h2 className="text-xl font-semibold mb-6 text-center">Основной пайплайн</h2>

        <div className="flex flex-col items-center">
          {/* Data sources */}
          <div className="w-full grid grid-cols-2 md:grid-cols-4 gap-3 mb-2">
            {[
              "Посты канала (6000+)",
              "Статьи (35)",
              "Видео (34)",
              "Подкасты",
            ].map((src) => (
              <div
                key={src}
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2.5 text-center text-xs text-[var(--color-muted)]"
              >
                {src}
              </div>
            ))}
          </div>

          <Arrow />

          <div className="w-full max-w-md">
            <Block
              title="Embedding + ChromaDB"
              subtitle="Векторная база знаний"
              items={["ONNX embeddings", "6 регистров контента", "Семантический поиск"]}
            />
          </div>

          <Arrow />

          <div className="w-full max-w-md">
            <Block
              title="Voice Profile"
              subtitle="Профиль голоса Бескромного"
              items={["Стилистика", "Лексика", "Структура", "Интонации"]}
              accent
            />
          </div>

          <Arrow />

          <div className="w-full max-w-md">
            <Block
              title="LLM (Claude)"
              subtitle="Генерация контента"
              items={["RAG-контекст", "Промпт с голосом", "Мультирегистровость"]}
              accent
            />
          </div>

          <Arrow />

          <div className="w-full max-w-md">
            <Block
              title="Telegram-бот"
              subtitle="Интерфейс пользователя"
              items={["/post", "/rewrite", "/comment", "/idea", "/analyze"]}
            />
          </div>

          <Arrow />

          <div className="w-full max-w-md">
            <Block title="Пользователь (Дмитрий)" subtitle="Использует, редактирует или отклоняет" />
          </div>
        </div>
      </section>

      {/* Feedback loop */}
      <section className="mt-16 animate-fade-in-up animate-delay-200">
        <h2 className="text-xl font-semibold mb-6 text-center">Петля обратной связи</h2>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-6">
          <div className="grid md:grid-cols-3 gap-4">
            <div className="rounded-lg border border-green-900/50 bg-green-950/30 p-4 text-center">
              <div className="text-2xl mb-2">&#10003;</div>
              <div className="font-medium text-green-400 text-sm">Использовал</div>
              <div className="text-xs text-[var(--color-muted)] mt-1">
                Текст принят как есть — сигнал высокого качества
              </div>
            </div>
            <div className="rounded-lg border border-yellow-900/50 bg-yellow-950/30 p-4 text-center">
              <div className="text-2xl mb-2">&#9998;</div>
              <div className="font-medium text-yellow-400 text-sm">Отредактировал</div>
              <div className="text-xs text-[var(--color-muted)] mt-1">
                Текст доработан — система учится на правках
              </div>
            </div>
            <div className="rounded-lg border border-red-900/50 bg-red-950/30 p-4 text-center">
              <div className="text-2xl mb-2">&#10007;</div>
              <div className="font-medium text-red-400 text-sm">Отклонил</div>
              <div className="text-xs text-[var(--color-muted)] mt-1">
                Текст не подошёл — негативный сигнал для модели
              </div>
            </div>
          </div>
          <div className="mt-4 text-center text-xs text-[var(--color-muted)]">
            Все решения сохраняются в SQLite и используются для улучшения промптов
          </div>
        </div>
      </section>

      {/* Tech stack */}
      <section className="mt-16 animate-fade-in-up animate-delay-300">
        <h2 className="text-xl font-semibold mb-6 text-center">Технологический стек</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[
            { name: "Python 3.11+", role: "Backend" },
            { name: "Claude API", role: "LLM" },
            { name: "ChromaDB", role: "Векторная БД" },
            { name: "SQLite", role: "Обратная связь" },
            { name: "OpenAI Embeddings", role: "Эмбеддинги" },
            { name: "python-telegram-bot", role: "Telegram" },
            { name: "Next.js 15", role: "Frontend" },
            { name: "Tailwind CSS", role: "Стилизация" },
            { name: "Vercel", role: "Хостинг" },
          ].map((tech) => (
            <div
              key={tech.name}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-3 text-center"
            >
              <div className="text-sm font-medium">{tech.name}</div>
              <div className="text-xs text-[var(--color-muted)] mt-0.5">{tech.role}</div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
