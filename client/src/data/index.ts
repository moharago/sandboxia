import projectsData from "./projects.json"
import tracksData from "./tracks.json"

import type { Project } from "@/types/data/project"
import type { Track } from "@/types/data/track"

export const projects: Project[] = projectsData as Project[]
export const tracks: Track[] = tracksData as Track[]
