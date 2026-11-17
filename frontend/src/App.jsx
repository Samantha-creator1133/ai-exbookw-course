import { useEffect, useState } from "react";

async function readJson(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Помилка сервера (${response.status})`);
  return data;
}

function Loading({ children }) {
  return <div className="state-box" role="status"><span className="spinner" />{children}</div>;
}

function ErrorBox({ message, retry }) {
  return <div className="state-box error-box" role="alert"><span>{message}</span><button onClick={retry}>Спробувати ще раз</button></div>;
}

function formatDate(value) {
  return new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function App() {
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState("");
  const [statsReload, setStatsReload] = useState(0);
  const [searches, setSearches] = useState([]);
  const [searchesLoading, setSearchesLoading] = useState(true);
  const [searchesError, setSearchesError] = useState("");
  const [searchReload, setSearchReload] = useState(0);
  const [moods, setMoods] = useState([]);
  const [moodsLoading, setMoodsLoading] = useState(true);
  const [moodsError, setMoodsError] = useState("");
  const [moodsReload, setMoodsReload] = useState(0);
  const [selectedMoodId, setSelectedMoodId] = useState("");
  const [result, setResult] = useState(null);
  const [resultLoading, setResultLoading] = useState(false);
  const [resultError, setResultError] = useState("");
  const [resultReload, setResultReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStatsLoading(true);
    setStatsError("");
    fetch("/api/admin/stats", { signal: controller.signal })
      .then(readJson).then(setStats)
      .catch((error) => { if (error.name !== "AbortError") setStatsError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setStatsLoading(false); });
    return () => controller.abort();
  }, [statsReload]);

  useEffect(() => {
    const controller = new AbortController();
    setSearchesLoading(true);
    setSearchesError("");
    fetch("/api/admin/mood-searches?limit=100", { signal: controller.signal })
      .then(readJson).then(setSearches)
      .catch((error) => { if (error.name !== "AbortError") setSearchesError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setSearchesLoading(false); });
    return () => controller.abort();
  }, [searchReload]);

  useEffect(() => {
    const controller = new AbortController();
    setMoodsLoading(true);
    setMoodsError("");
    fetch("/api/users-mood", { signal: controller.signal })
      .then(readJson)
      .then((data) => {
        if (!Array.isArray(data)) throw new Error("Сервер повернув некоректний список настроїв.");
        setMoods(data);
        setSelectedMoodId((current) => current && data.some((mood) => String(mood.id) === current) ? current : data.length ? String(data[0].id) : "");
      })
      .catch((error) => { if (error.name !== "AbortError") setMoodsError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setMoodsLoading(false); });
    return () => controller.abort();
  }, [moodsReload]);

  useEffect(() => {
    if (!selectedMoodId) { setResult(null); setResultLoading(false); return undefined; }
    const controller = new AbortController();
    setResultLoading(true);
    setResultError("");
    fetch(`/api/result?mood_id=${encodeURIComponent(selectedMoodId)}`, { signal: controller.signal })
      .then(readJson).then(setResult)
      .catch((error) => { if (error.name !== "AbortError") setResultError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setResultLoading(false); });
    return () => controller.abort();
  }, [selectedMoodId, resultReload]);

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <a className="brand" href="#overview"><span className="brand-icon">К</span><span>Книжкова<br />адмінка</span></a>
        <div className="side-label">РОБОЧИЙ ПРОСТІР</div>
        <a className="nav-link active" href="#requests"><span>▤</span> Запити користувачів</a>
        <a className="nav-link" href="#catalog"><span>▣</span> Каталог настроїв</a>
        <div className="sidebar-bottom"><span className="online-dot" /> API підключено</div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar">
          <div><p className="breadcrumb">ПАНЕЛЬ КЕРУВАННЯ <span>/</span> ОГЛЯД</p><h1>Огляд</h1></div>
          <div className="admin-profile"><div className="avatar">A</div><div><strong>Адміністратор</strong><small>Книжковий сервіс</small></div></div>
        </header>

        <section className="overview-cards" aria-label="Загальна статистика">
          <article className="metric-card"><span className="metric-icon violet">↗</span><span className="metric-label">Кількість запитів</span><strong>{statsLoading ? "—" : stats?.request_count ?? "—"}</strong><small>Уся історія mood_searches</small></article>
          <article className="metric-card"><span className="metric-icon mint">▤</span><span className="metric-label">Книг у бібліотеці</span><strong>{statsLoading ? "—" : stats?.book_count ?? "—"}</strong><small>У каталозі books</small></article>
          <article className="metric-card"><span className="metric-icon peach">☺</span><span className="metric-label">Можливі настрої та фрази</span><strong>{statsLoading ? "—" : `${stats?.mood_count ?? 0} / ${stats?.search_phrase_count ?? 0}`}</strong><small>Кожен настрій зараз є фразою пошуку</small></article>
        </section>
        {statsError && <ErrorBox message={statsError} retry={() => setStatsReload((key) => key + 1)} />}

        <section className="panel requests-panel" id="requests">
          <div className="panel-heading">
            <div><p className="eyebrow">АКТИВНІСТЬ</p><h2>Запити користувачів</h2><p className="panel-subtitle">Історія настроїв і книжкових рекомендацій</p></div>
            <button className="refresh-button" onClick={() => setSearchReload((key) => key + 1)} aria-label="Оновити запити">⟳ <span>Оновити</span></button>
          </div>
          {searchesLoading ? <Loading>Завантажуємо історію запитів…</Loading> : searchesError ? <ErrorBox message={searchesError} retry={() => setSearchReload((key) => key + 1)} /> : searches.length === 0 ? <div className="empty-state"><span>▤</span><strong>Запитів поки немає</strong><p>Коли користувачі почнуть надсилати настрій боту, вони з’являться тут.</p></div> : (
            <div className="table-scroll"><table><thead><tr><th>КОРИСТУВАЧ</th><th>ЗАПИТ</th><th>ВИЗНАЧЕНИЙ НАСТРІЙ</th><th>РЕКОМЕНДОВАНІ КНИГИ</th><th>ДАТА</th></tr></thead>
              <tbody>{searches.map((search) => <tr key={search.id}>
                <td><div className="user-cell"><span className="user-avatar">{(search.username || "?").replace(/^@/, "").slice(0, 1).toUpperCase()}</span><div><strong>{search.username ? `@${search.username.replace(/^@/, "")}` : "Без username"}</strong><small>Запит №{search.id}</small></div></div></td>
                <td><span className="mood-quote">“{search.mood_text}”</span></td>
                <td>{search.matched_mood ? <span className="mood-badge">{search.matched_mood}</span> : <span className="unmatched">Не визначено</span>}</td>
                <td>{search.recommendations.length ? <div className="recommendation-list">{search.recommendations.map((book, index) => <span key={`${book.title}-${index}`}><strong>{book.title}</strong>{book.author && <small>{book.author}</small>}</span>)}</div> : <span className="unmatched">Немає рекомендацій</span>}</td>
                <td className="date-cell">{formatDate(search.created_at)}</td>
              </tr>)}</tbody></table></div>
          )}
          <div className="table-footer">Показано {searchesLoading ? "—" : searches.length} останніх запитів <span>Джерело: mood_searches</span></div>
        </section>

        <section className="panel catalog-panel" id="catalog">
          <div className="panel-heading compact-heading"><div><p className="eyebrow">КАТАЛОГ</p><h2>Перевірка рекомендацій</h2><p className="panel-subtitle">Переглянь книги, пов’язані з настроєм</p></div></div>
          {moodsLoading ? <Loading>Завантажуємо настрої…</Loading> : moodsError ? <ErrorBox message={moodsError} retry={() => setMoodsReload((key) => key + 1)} /> : moods.length === 0 ? <div className="empty-state"><strong>Каталог настроїв порожній</strong><p>Додай настрої та книги до бази даних, щоб побачити рекомендації.</p></div> : <div className="catalog-content">
            <label htmlFor="mood-select">Оберіть настрій</label><select id="mood-select" value={selectedMoodId} onChange={(event) => setSelectedMoodId(event.target.value)}>{moods.map((mood) => <option key={mood.id} value={mood.id}>{mood.name}</option>)}</select>
            <div className="book-results">{resultLoading ? <Loading>Завантажуємо книги…</Loading> : resultError ? <ErrorBox message={resultError} retry={() => setResultReload((key) => key + 1)} /> : result?.books?.length ? result.books.map((book, index) => <article className="book-row" key={`${book.title}-${index}`}><span className="book-index">{String(index + 1).padStart(2, "0")}</span><div><strong>{book.title}</strong><small>{book.author || "Автор невідомий"}</small>{book.description && <p>{book.description}</p>}</div></article>) : <p className="no-books">Для цього настрою поки немає рекомендованих книг.</p>}</div>
          </div>}
        </section>
        <footer className="footer"><span>Книжкова адмінка</span><span>Дані оновлюються з Neon</span></footer>
      </main>
    </div>
  );
}
