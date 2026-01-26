import { HeroSection } from "@/components/features/landing/HeroSection"
import { FeatureSection } from "@/components/features/landing/FeatureSection"
import { FlowSection } from "@/components/features/landing/FlowSection"
import { CTASection } from "@/components/features/landing/CTASection"

export default function LandingPage() {
    return (
        <>
            <HeroSection />
            <FeatureSection />
            <FlowSection />
            <CTASection />
        </>
    )
}
