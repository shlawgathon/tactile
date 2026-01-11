import AuthenticatedLayout from "../../components/AuthenticatedLayout";
import "@crayonai/react-ui/styles/index.css";

export default function DashboardLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return <AuthenticatedLayout>{children}</AuthenticatedLayout>;
}
