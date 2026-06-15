import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { StoreProvider } from "@/store";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "GradeMIND - AI-Powered Exam Grading & Evaluation Analytics",
  description: "Scaling classroom assessment using advanced AI analytics, student response sheets grading and detailed reports generation.",
  icons: {
    icon: "/images/grademind-logo-official.jpeg",
    shortcut: "/images/grademind-logo-official.jpeg",
    apple: "/images/grademind-logo-official.jpeg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} font-sans antialiased`}
      >
        <StoreProvider>{children}</StoreProvider>
      </body>
    </html>
  );
}
