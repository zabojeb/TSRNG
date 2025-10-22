import { NavLink } from "react-router-dom";
import { PropsWithChildren } from "react";

const links = [
  { to: "/", label: "Главная" },
  { to: "/generate", label: "Генерация" },
  { to: "/analysis", label: "Анализ" },
  { to: "/how-it-works", label: "Как это работает?" },
];

function Layout({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white via-brand-light/50 to-white">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <NavLink
            to="/"
            className="text-xl font-semibold tracking-tight text-brand-dark"
          >
            RandomTrust TSRNG
          </NavLink>
          <nav className="flex gap-5 text-sm font-medium">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `transition-colors ${
                    isActive ? "text-brand-yellow" : "text-slate-500 hover:text-brand-dark"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main>{children}</main>
      <footer className="border-t border-slate-200 bg-white/80 py-6">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 text-sm text-slate-500 md:flex-row md:items-center md:justify-between">
          <span>© {new Date().getFullYear()} RandomTrust. Прозрачный ГСЧ.</span>
          <span>Backend API: <code>http://127.0.0.1:8000</code></span>
        </div>
      </footer>
    </div>
  );
}

export default Layout;
