import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Playfair_Display } from "next/font/google";
import { StoreProvider } from "@/store";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
  weight: ["400", "500", "600", "700", "800"],
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  weight: ["600", "700", "800", "900"],
});

export const metadata: Metadata = {
  title: "GradeMIND - AI-Powered Exam Grading & Evaluation Analytics",
  description: "Scaling classroom assessment using advanced AI analytics, student response sheets grading and detailed reports generation.",
  icons: {
    icon: "/images/logo.png",
    shortcut: "/images/logo.png",
    apple: "/images/logo.png",
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
        className={`${jakarta.variable} ${playfair.variable} font-sans antialiased bg-[#F4F8F3] text-black`}
      >
        <StoreProvider>{children}</StoreProvider>
      </body>
    </html>
  );
}
