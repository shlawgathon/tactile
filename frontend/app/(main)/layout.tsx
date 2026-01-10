import AuthenticatedLayout from "../../components/AuthenticatedLayout";

export default function DashboardLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return <AuthenticatedLayout>{children}</AuthenticatedLayout>;
}
