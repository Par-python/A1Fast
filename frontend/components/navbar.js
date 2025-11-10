'use client';

export default function NavBar() {
  return (
    <nav className="relative flex items-center justify-between px-8 py-4">
      {/* Left: Logo */}
      <div className="text-2xl font-bold text-white">
        S<span className="text-purple-500">1</span>
      </div>

      {/* Center: Links */}
      <div className="absolute left-1/2 -translate-x-1/2 flex gap-10 text-white/90 text-lg">
        <a href="#" className="hover:text-purple-400 transition-colors">
          Leaderboards
        </a>
        <a href="#" className="hover:text-purple-400 transition-colors">
          Documentation
        </a>
      </div>

      {/* Right: Login button */}
      <button className="bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium px-6 py-2 rounded-full flex items-center gap-2 transition-colors">
        Login
        <span className="text-lg">→</span>
      </button>
    </nav>
  );
}
