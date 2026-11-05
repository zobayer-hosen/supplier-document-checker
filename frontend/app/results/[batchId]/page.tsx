import { Suspense } from "react";
import { BatchResults } from "@/components/BatchResults";
import { Loading } from "@/components/StateMessages";

// BatchResults reads the batch id from the URL, so it must sit inside Suspense.
export default function ResultsPage() {
  return (
    <Suspense fallback={<Loading label="Loading batch..." />}>
      <BatchResults />
    </Suspense>
  );
}
