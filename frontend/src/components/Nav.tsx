import Link from "next/link";
import { Wordmark } from "@/components/Wordmark";

export function Nav() {
  return (
    <header className="w-full">
      <div className="mx-auto flex max-w-(--container-wide) items-center justify-between px-6 pt-8 md:px-12 md:pt-12">
        <Link href="/" aria-label="Aegis home">
          <Wordmark />
        </Link>
        <nav
          aria-label="Primary"
          className="flex items-center gap-6 font-body text-sm text-text-secondary md:gap-8"
        >
          <Link href="/appeal" className="transition-colors hover:text-text-primary">
            Draft an appeal
          </Link>
          <Link href="/showcase" className="transition-colors hover:text-text-primary">
            How Aegis learns
          </Link>
        </nav>
      </div>
    </header>
  );
}
