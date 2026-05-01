type Message = {
  role: "user" | "bot";
  text: string;
};

const conversations: { command: string; messages: Message[] }[] = [
  {
    command: "/post",
    messages: [
      { role: "user", text: "/post Почему медиа — это новая нефть" },
      {
        role: "bot",
        text: `Медиа — это новая нефть. Не в метафорическом смысле, а в самом что ни на есть экономическом.

Когда я начинал в медиа 15 лет назад, главным активом были связи. Потом — контент. Сейчас — внимание. И тот, кто умеет конвертировать внимание в доверие, а доверие — в деньги, владеет настоящей скважиной.

Посмотрите на любой успешный бизнес последних пяти лет. За каждым стоит медийная машина. Не рекламный бюджет, а именно машина: системное производство контента, личный бренд основателя, комьюнити.

Нефть когда-то тоже была просто чёрной жижей, пока кто-то не научился её перерабатывать. С медиа — та же история.`,
      },
    ],
  },
  {
    command: "/rewrite",
    messages: [
      {
        role: "user",
        text: `/rewrite Искусственный интеллект меняет мир. Все компании должны внедрять AI. Это очень важно для будущего.`,
      },
      {
        role: "bot",
        text: `AI не «меняет мир» — он уже его изменил. Пока одни пишут стратегии внедрения, другие уже автоматизировали половину процессов.

Мне не нравится слово «должны». Никто никому ничего не должен. Но те, кто игнорирует AI сегодня, через два года будут объяснять акционерам, почему конкуренты работают в три раза быстрее при вдвое меньших затратах.

Это не про будущее. Это про настоящее, которое уже наступило.`,
      },
    ],
  },
  {
    command: "/comment",
    messages: [
      {
        role: "user",
        text: "/comment https://t.me/channel/post123 (пост про выгорание в медиа)",
      },
      {
        role: "bot",
        text: `Выгорание в медиа — это не когда ты устал. Это когда ты перестал чувствовать кайф от того, что делаешь.

Я прошёл через это дважды. Оба раза выход был один — не «отдых», а смена оптики. Когда начинаешь делать не «для аудитории», а потому что тебе самому интересно, энергия возвращается.

Главная ловушка — путать системность с рутиной. Система должна освобождать, а не порабощать.`,
      },
    ],
  },
];

function BotAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent)] text-xs font-bold text-white">
      GPT
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-700 text-xs font-bold text-white">
      Д
    </div>
  );
}

export default function ChatPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <div className="animate-fade-in-up">
        <h1 className="text-3xl font-bold mb-2">Демо чат-бота</h1>
        <p className="text-[var(--color-muted)] mb-8">
          Примеры работы Telegram-бота БескромныйGPT. Это статичная демонстрация
          — реальный бот работает в Telegram.
        </p>
      </div>

      <div className="space-y-12">
        {conversations.map((conv, ci) => (
          <div key={ci} className="animate-fade-in-up" style={{ animationDelay: `${ci * 0.15}s` }}>
            <div className="mb-3 inline-block rounded-full border border-[var(--color-accent)]/30 bg-[var(--color-accent)]/10 px-3 py-1 text-xs text-[var(--color-accent)] font-mono">
              {conv.command}
            </div>
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-4 space-y-4">
              {conv.messages.map((msg, mi) => (
                <div
                  key={mi}
                  className={`flex gap-3 ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {msg.role === "bot" && <BotAvatar />}
                  <div
                    className={`max-w-[85%] rounded-lg px-4 py-3 text-sm leading-relaxed whitespace-pre-line ${
                      msg.role === "user"
                        ? "bg-[var(--color-accent)] text-white rounded-br-sm"
                        : "bg-zinc-800 text-zinc-200 rounded-bl-sm"
                    }`}
                  >
                    {msg.text}
                  </div>
                  {msg.role === "user" && <UserAvatar />}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-12 rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-6 animate-fade-in-up animate-delay-400">
        <h2 className="text-lg font-semibold mb-3">Все команды бота</h2>
        <div className="grid grid-cols-2 gap-2 text-sm">
          {[
            ["/post", "Генерация поста на тему"],
            ["/rewrite", "Переписать текст в голосе"],
            ["/comment", "Комментарий к посту"],
            ["/idea", "Идеи для контента"],
            ["/analyze", "Анализ текста"],
            ["/voice", "Профиль голоса"],
            ["/help", "Список команд"],
          ].map(([cmd, desc]) => (
            <div key={cmd} className="flex gap-2">
              <span className="font-mono text-[var(--color-accent)]">{cmd}</span>
              <span className="text-[var(--color-muted)]">— {desc}</span>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
