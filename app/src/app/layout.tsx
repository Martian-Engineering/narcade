import type { Metadata } from "next";
import { Pixelify_Sans, Press_Start_2P } from "next/font/google";
import "./globals.css";

const pixel = Pixelify_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-pixel",
});

const display = Press_Start_2P({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "NARCADE — Model Gameplay Leaderboard",
  description: "Non-Autoregressive Ranking and Choice Across Discrete Environments.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${pixel.variable} ${display.variable}`}>{children}</body>
    </html>
  );
}
