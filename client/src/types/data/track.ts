export type TrackType = "demonstration" | "temporary" | "fastcheck"

export interface Track {
    id: string
    type: TrackType
    name: string
    description: string
    duration: string
    requirements: string[]
    benefits: string[]
    bestFor: string[]
}

export const TRACK_LABELS: Record<TrackType, string> = {
    demonstration: "실증특례",
    temporary: "임시허가",
    fastcheck: "신속확인",
}
