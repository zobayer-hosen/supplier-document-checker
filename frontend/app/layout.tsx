import type { Metadata } from "next";
import { Suspense } from "react";
import { NavBar } from "@/components/NavBar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Supplier Document Checker",
  description: "Checks supplier quotations against the purchase request and company rules.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        {/* NavBar reads the current URL, so it needs a Suspense boundary on dynamic pages. */}
        <Suspense fallback={<div className="h-[57px] border-b border-slate-200 bg-white" />}>
          <NavBar />
        </Suspense>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
