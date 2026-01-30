import { redirect } from "next/navigation"

interface CasePageProps {
    params: Promise<{ id: string }>
}

export default async function CasePage({ params }: CasePageProps) {
    const { id } = await params
    redirect(`/projects/${id}/service`)
}
