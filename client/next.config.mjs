/** @type {import('next').NextConfig} */
const nextConfig = {
    /* config options here */
    reactCompiler: true,

    // API 프록시
    // Vercel에서 EC2 HTTP 서버로 프록시
    async rewrites() {
        const backendUrl = process.env.BACKEND_URL || "http://localhost:8000"

        return [
            {
                source: "/api/v1/:path*",
                destination: `${backendUrl}/api/v1/:path*`,
            },
            {
                source: "/api/users/:path*",
                destination: `${backendUrl}/api/users/:path*`,
            },
        ]
    },
    devIndicators: false,
}

export default nextConfig
