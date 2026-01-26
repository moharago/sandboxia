import type { ReactNode } from "react";
import { MainLayout } from "@/components/layouts/MainLayout";

interface MarketingLayoutProps {
    children: ReactNode;
}

export default function MarketingLayout({ children }: MarketingLayoutProps) {
    return <MainLayout>{children}</MainLayout>;
}
