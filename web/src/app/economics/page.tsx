const costItems = [
  {
    category: "Разработка",
    items: [
      {
        name: "Стоимость разработки",
        cost: "~0 &#8381;",
        note: "Vibe-coded с помощью AI (Claude Code, Cursor)",
      },
      {
        name: "Время разработки",
        cost: "~40 часов",
        note: "Суммарно на все компоненты системы",
      },
    ],
  },
  {
    category: "API и модели",
    items: [
      {
        name: "LLM (OpenRouter / Claude)",
        cost: "~$0.05 / запрос",
        note: "Средняя стоимость одной генерации",
      },
      {
        name: "Embeddings",
        cost: "Бесплатно",
        note: "Локальная ONNX-модель, без API-вызовов",
      },
    ],
  },
  {
    category: "Инфраструктура",
    items: [
      {
        name: "ChromaDB",
        cost: "Бесплатно",
        note: "Локальная векторная база данных",
      },
      {
        name: "SQLite",
        cost: "Бесплатно",
        note: "Локальное хранение обратной связи",
      },
      {
        name: "Telegram Bot API",
        cost: "Бесплатно",
        note: "Бесплатный API от Telegram",
      },
      {
        name: "Vercel хостинг",
        cost: "Бесплатно",
        note: "Hobby-план для веб-витрины",
      },
    ],
  },
];

const keyPoints = [
  {
    icon: "&#128176;",
    title: "Нулевой бюджет на разработку",
    description:
      "Весь проект создан одним человеком с помощью AI-инструментов. Без команды, без аутсорса, без бюджета.",
  },
  {
    icon: "&#9889;",
    title: "Минимальные операционные расходы",
    description:
      "Единственная переменная статья — API-вызовы к LLM. При 100 генерациях в месяц это ~$5.",
  },
  {
    icon: "&#127793;",
    title: "Полностью локальная инфраструктура",
    description:
      "ChromaDB, SQLite, embeddings — всё работает локально. Нет облачных подписок, нет vendor lock-in.",
  },
  {
    icon: "&#128200;",
    title: "Масштабируемость без затрат",
    description:
      "Добавление новых данных в RAG стоит $0. Стоимость растёт только с количеством генераций.",
  },
];

export default function EconomicsPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-16">
      <div className="animate-fade-in-up">
        <h1 className="text-3xl font-bold mb-2">Экономика проекта</h1>
        <p className="text-[var(--color-muted)] mb-12">
          Сколько стоит создать и поддерживать персональную AI-систему для личного бренда.
        </p>
      </div>

      {/* Cost breakdown */}
      <section className="space-y-8 animate-fade-in-up animate-delay-100">
        {costItems.map((group) => (
          <div key={group.category}>
            <h2 className="text-lg font-semibold mb-3 text-[var(--color-accent)]">
              {group.category}
            </h2>
            <div className="space-y-2">
              {group.items.map((item) => (
                <div
                  key={item.name}
                  className="flex flex-col sm:flex-row sm:items-center justify-between rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-4 gap-2"
                >
                  <div>
                    <div className="font-medium text-sm">{item.name}</div>
                    <div className="text-xs text-[var(--color-muted)]">{item.note}</div>
                  </div>
                  <div
                    className="text-lg font-bold text-[var(--color-accent)] whitespace-nowrap"
                    dangerouslySetInnerHTML={{ __html: item.cost }}
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      {/* Monthly estimate */}
      <section className="mt-12 animate-fade-in-up animate-delay-200">
        <div className="rounded-xl border border-[var(--color-accent)]/30 bg-[var(--color-accent)]/5 p-6 text-center">
          <div className="text-sm text-[var(--color-muted)] mb-2">
            Итого ежемесячные расходы (при 100 генерациях)
          </div>
          <div className="text-4xl font-bold text-[var(--color-accent)]">~$5</div>
          <div className="text-sm text-[var(--color-muted)] mt-2">
            Только API-вызовы к LLM. Всё остальное — бесплатно.
          </div>
        </div>
      </section>

      {/* Key points */}
      <section className="mt-12 grid md:grid-cols-2 gap-4 animate-fade-in-up animate-delay-300">
        {keyPoints.map((point) => (
          <div
            key={point.title}
            className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-5"
          >
            <div
              className="text-2xl mb-2"
              dangerouslySetInnerHTML={{ __html: point.icon }}
            />
            <h3 className="font-semibold text-sm mb-1">{point.title}</h3>
            <p className="text-xs text-[var(--color-muted)] leading-relaxed">
              {point.description}
            </p>
          </div>
        ))}
      </section>

      {/* Comparison */}
      <section className="mt-12 animate-fade-in-up animate-delay-400">
        <h2 className="text-lg font-semibold mb-4">Сравнение с альтернативами</h2>
        <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] bg-[var(--color-card)]">
                <th className="px-4 py-3 text-left font-medium text-[var(--color-muted)]">
                  Подход
                </th>
                <th className="px-4 py-3 text-left font-medium text-[var(--color-muted)]">
                  Разработка
                </th>
                <th className="px-4 py-3 text-left font-medium text-[var(--color-muted)]">
                  В месяц
                </th>
                <th className="px-4 py-3 text-left font-medium text-[var(--color-muted)]">
                  Контроль
                </th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-[var(--color-border)] bg-[var(--color-accent)]/5">
                <td className="px-4 py-3 font-medium text-[var(--color-accent)]">
                  БескромныйGPT
                </td>
                <td className="px-4 py-3">~0 &#8381;</td>
                <td className="px-4 py-3">~$5</td>
                <td className="px-4 py-3">Полный</td>
              </tr>
              <tr className="border-b border-[var(--color-border)]">
                <td className="px-4 py-3 font-medium">Фрилансер</td>
                <td className="px-4 py-3">300-500K &#8381;</td>
                <td className="px-4 py-3">50-100K &#8381;</td>
                <td className="px-4 py-3">Средний</td>
              </tr>
              <tr className="border-b border-[var(--color-border)]">
                <td className="px-4 py-3 font-medium">Агентство</td>
                <td className="px-4 py-3">1-3M &#8381;</td>
                <td className="px-4 py-3">200-500K &#8381;</td>
                <td className="px-4 py-3">Низкий</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">SaaS-платформа</td>
                <td className="px-4 py-3">0 &#8381;</td>
                <td className="px-4 py-3">$50-200</td>
                <td className="px-4 py-3">Минимальный</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
