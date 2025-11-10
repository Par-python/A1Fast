import NavBar from "../../components/navbar";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-zinc-50 font-sans dark:bg-black">

      <NavBar />

      <main className="flex flex-1 items-center justify-center">
        <h1 className="text-3xl font-bold text-white">Welcome</h1>
      </main>
    </div>
  );
}
