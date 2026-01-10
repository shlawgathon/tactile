import SideNav from "../../components/SideNav";
import TopNav from "../../components/TopNav";
import { DM_Mono } from "next/font/google";

const dm_mono = DM_Mono({
    weight: ["300", "400", "500"],
    subsets: ["latin"],
});

export default function DashboardLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const user = { email: "wes@tactile.com", uid: "123" };
    const projects = [
        { id: "1", name: "Tactile" },
        { id: "2", name: "Engineering" }
    ];

    return (
        <div className={`${dm_mono.className} flex h-screen w-full bg-white text-black font-sans selection:bg-zinc-200 overflow-hidden`}>
            <SideNav user={user} userData={{}} projects={projects} title="Tactile" />
            <div className="flex flex-col flex-1 h-full min-w-0">
                <TopNav user={user} />
                <main className="flex-1 overflow-y-auto bg-gray-50 p-6 scrollbar-thin scrollbar-thumb-zinc-300 scrollbar-track-transparent">
                    {children}
                </main>
            </div>
        </div>
    );
}
