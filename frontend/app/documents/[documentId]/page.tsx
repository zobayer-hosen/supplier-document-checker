import { Suspense } from "react";
import { DocumentDetails } from "@/components/DocumentDetails";
import { Loading } from "@/components/StateMessages";

// DocumentDetails reads the document id from the URL, so it must sit inside Suspense.
export default function DocumentPage() {
  return (
    <Suspense fallback={<Loading label="Loading supplier details..." />}>
      <DocumentDetails />
    </Suspense>
  );
}
