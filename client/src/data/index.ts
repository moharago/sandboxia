import casesData from './cases.json';
import tracksData from './tracks.json';
import domainsData from './domains.json';

import type { Case, Track, Domain } from '@/types/data';

export const cases: Case[] = casesData as Case[];
export const tracks: Track[] = tracksData as Track[];
export const domains: Domain[] = domainsData as Domain[];
