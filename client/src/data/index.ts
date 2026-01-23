import casesData from './cases.json';
import tracksData from './tracks.json';

import type { Case, Track } from '@/types/data';

export const cases: Case[] = casesData as Case[];
export const tracks: Track[] = tracksData as Track[];
