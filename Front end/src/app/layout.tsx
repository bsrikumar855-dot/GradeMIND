import type { Metadata } from "next";
import { Playfair_Display } from "next/font/google";
import { StoreProvider } from "@/store";
import "./globals.css";

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
});

export const metadata: Metadata = {
  title: "GradeMIND - AI-Powered Exam Grading & Evaluation Analytics",
  description: "Scaling classroom assessment using advanced AI analytics, student response sheets grading and detailed reports generation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${playfair.variable} font-sans antialiased`}
      >
        <StoreProvider>{children}</StoreProvider>
      </body>
    </html>
  );
}
