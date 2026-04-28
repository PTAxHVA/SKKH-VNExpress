import { CityMapSection } from "@/components/sections/city-map";
import { DemoVideoSection } from "@/components/sections/demo-video";
import { EmissionCalculator } from "@/components/sections/emission-calculator";
import { Hero } from "@/components/sections/hero";
import { ImpactSection } from "@/components/sections/impact";
import { PipelineSection } from "@/components/sections/pipeline";
import { ProblemSection } from "@/components/sections/problem";
import { ResultsSection } from "@/components/sections/results";
import { TeamCTASection } from "@/components/sections/team-cta";
import { loadEmissionsDataset } from "@/lib/load-emissions-dataset";
import { loadEmissionsReport } from "@/lib/load-emissions-report";

export default async function LandingPage() {
  const [report, dataset] = await Promise.all([
    loadEmissionsReport(),
    loadEmissionsDataset(100)
  ]);

  return (
    <main id="main-content">
      <Hero />
      <ProblemSection />
      <PipelineSection />
      <EmissionCalculator />
      <ResultsSection report={report} dataset={dataset} />
      <DemoVideoSection />
      <CityMapSection />
      <ImpactSection />
      <TeamCTASection />
    </main>
  );
}
