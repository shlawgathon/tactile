import { DM_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from 'react-hot-toast';

const dm_mono = DM_Mono({
  weight: ["300", "400", "500"],
  subsets: ["latin"],
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${dm_mono.className} antialiased text-black bg-white bg-[radial-gradient(#2b2b2b_1px,transparent_1px)] [background-size:35px_35px]`}
      >
        {children}
        <Toaster position="bottom-right" />
      </body>
    </html>
  );
}
