import type { CaseDomain } from './case';

export interface Domain {
  id: CaseDomain;
  name: string;
  description: string;
  icon: string;
  examples: string[];
}
