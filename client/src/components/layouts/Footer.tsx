import Link from "next/link";

interface FooterLink {
    label: string;
    href: string;
}

const footerLinks: FooterLink[] = [
    { label: "이용약관", href: "/terms" },
    { label: "개인정보처리방침", href: "/privacy" },
    { label: "고객센터", href: "/support" },
];

export function Footer() {
    return (
        <footer className="border-t border-border bg-muted/30">
            <div className="container mx-auto px-4 py-8">
                <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">
                            <span className="text-gray-900">Sandbox</span>
                            <span className="text-teal-9">IA</span>
                        </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                        &copy; {new Date().getFullYear()} SandboxIA. All rights
                        reserved.
                    </p>

                    {/* <nav className="flex items-center gap-6">
            {footerLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </nav> */}
                </div>

                {/* <div className="mt-6 pt-6 border-t border-border text-center text-xs text-muted-foreground">
          <p>
            &copy; {new Date().getFullYear()} SandboxIA. All rights reserved.
          </p>
        </div> */}
            </div>
        </footer>
    );
}
