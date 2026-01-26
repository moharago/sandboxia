import casesData from "./cases.json"
import tracksData from "./tracks.json"

import type { Case } from "@/types/data/case"
import type { Track } from "@/types/data/track"

export const cases: Case[] = casesData as Case[]
export const tracks: Track[] = tracksData as Track[]
