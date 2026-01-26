import { Check, Clock, ChevronRight } from "lucide-react"
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { Track, TrackType } from "@/types/data/track"
import { cn } from "@/lib/utils/cn"

interface TrackCardProps {
    track: Track
    isRecommended?: boolean
    isSelected?: boolean
    onSelect?: (trackId: string) => void
    score?: number
}

const trackColors: Record<TrackType, string> = {
    demonstration: "from-blue-500 to-blue-600",
    temporary: "from-grass-500 to-grass-600",
    fastcheck: "from-grass-500 to-grass-600",
}

export function TrackCard({ track, isRecommended = false, isSelected = false, onSelect, score }: TrackCardProps) {
    return (
        <Card
            className={cn(
                "relative overflow-hidden transition-all cursor-pointer hover:shadow-lg",
                isSelected && "ring-2 ring-primary",
                isRecommended && "border-primary"
            )}
            onClick={() => onSelect?.(track.id)}
        >
            {isRecommended && (
                <div className="absolute top-0 right-0">
                    <Badge className="rounded-none rounded-bl-lg bg-primary">추천</Badge>
                </div>
            )}

            <div className={cn("h-2 bg-gradient-to-r", trackColors[track.type])} />

            <CardHeader>
                <div className="flex items-start justify-between">
                    <div>
                        <h3 className="text-lg font-semibold">{track.name}</h3>
                        <p className="text-sm text-muted-foreground mt-1">{track.description}</p>
                    </div>
                    {score !== undefined && (
                        <div className="text-right">
                            <div className="text-2xl font-bold text-primary">{score}</div>
                            <div className="text-xs text-muted-foreground">점수</div>
                        </div>
                    )}
                </div>
            </CardHeader>

            <CardContent className="space-y-4">
                <div className="flex items-center gap-2 text-sm">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span>{track.duration}</span>
                </div>

                <div>
                    <h4 className="text-sm font-medium mb-2">주요 요건</h4>
                    <ul className="space-y-1">
                        {track.requirements.slice(0, 3).map((req, index) => (
                            <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
                                <Check className="h-4 w-4 text-grass-500 shrink-0 mt-0.5" />
                                {req}
                            </li>
                        ))}
                    </ul>
                </div>

                <div>
                    <h4 className="text-sm font-medium mb-2">적합한 경우</h4>
                    <ul className="space-y-1">
                        {track.bestFor.slice(0, 2).map((item, index) => (
                            <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
                                <ChevronRight className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                                {item}
                            </li>
                        ))}
                    </ul>
                </div>
            </CardContent>
        </Card>
    )
}
