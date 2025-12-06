// Verdict values matching backend Meta taxonomy
export const VERDICT = {
  FALSE: 'false',
  ALTERED: 'altered',
  PARTLY_FALSE: 'partly_false',
  MISSING_CONTEXT: 'missing_context',
  SATIRE: 'satire',
  TRUE: 'true',
  UNABLE_TO_VERIFY: 'unable_to_verify',
  NOT_FACT_CHECKABLE: 'not_fact_checkable',
  NOT_WORTH_CORRECTING: 'not_worth_correcting',
  ERROR: 'error'
} as const;

// Type derived from the const object
export type Verdict = typeof VERDICT[keyof typeof VERDICT];

// Type with null for optional fields
export type VerdictOrNull = Verdict | null;

// Helper functions
export function isPositiveVerdict(verdict: string | null | undefined): boolean {
  return verdict === VERDICT.TRUE;
}

export function isNegativeVerdict(verdict: string | null | undefined): boolean {
  return verdict === VERDICT.FALSE ||
         verdict === VERDICT.ALTERED ||
         verdict === VERDICT.PARTLY_FALSE;
}

export function getVerdictBadgeVariant(verdict: string | null | undefined) {
  switch(verdict) {
    case VERDICT.TRUE:
      return "default";
    case VERDICT.FALSE:
    case VERDICT.ALTERED:
      return "destructive";
    case VERDICT.PARTLY_FALSE:
      return "secondary";
    default:
      return "outline";
  }
}

export function getVerdictColorClass(verdict: string | null | undefined) {
  switch(verdict) {
    case VERDICT.TRUE:
      return "bg-green-100 text-green-800";
    case VERDICT.FALSE:
    case VERDICT.ALTERED:
      return "bg-red-100 text-red-800";
    case VERDICT.PARTLY_FALSE:
      return "bg-orange-100 text-orange-800";
    case VERDICT.MISSING_CONTEXT:
    case VERDICT.SATIRE:
      return "bg-yellow-100 text-yellow-800";
    case VERDICT.UNABLE_TO_VERIFY:
    case VERDICT.NOT_FACT_CHECKABLE:
    case VERDICT.NOT_WORTH_CORRECTING:
      return "bg-gray-100 text-gray-800";
    case VERDICT.ERROR:
    default:
      return "bg-gray-100 text-gray-800";
  }
}

export function getVerdictDisplayName(verdict: string | null | undefined): string {
  const displayNames: Record<string, string> = {
    [VERDICT.FALSE]: "False",
    [VERDICT.ALTERED]: "Altered Media",
    [VERDICT.PARTLY_FALSE]: "Partly False",
    [VERDICT.MISSING_CONTEXT]: "Missing Context",
    [VERDICT.SATIRE]: "Satire",
    [VERDICT.TRUE]: "True",
    [VERDICT.UNABLE_TO_VERIFY]: "Unable to Verify",
    [VERDICT.NOT_FACT_CHECKABLE]: "Not Fact-Checkable",
    [VERDICT.NOT_WORTH_CORRECTING]: "Not Worth Correcting",
    [VERDICT.ERROR]: "Error"
  };

  return displayNames[verdict || ''] || verdict || 'Error';
}