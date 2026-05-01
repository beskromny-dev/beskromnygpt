import type { Metadata } from "next";
import Nav from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "БескромныйGPT",
  description:
    "Персональная голосовая модель и машина полуавтоматизации личного бренда Дмитрия Бескромного",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" className="dark">
      <body className="antialiased">
        <Nav />
        <div className="pt-16">{children}</div>
      </body>
    </html>
  );
}
