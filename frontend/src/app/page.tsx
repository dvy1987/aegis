import Link from "next/link";
import { Button } from "@/components/Button";
import { Wordmark } from "@/components/Wordmark";
import { Nav } from "@/components/Nav";
import { ArrowRightIcon } from "@/icons";

export default function Home() {
  return (
    <div className="min-h-dvh flex flex-col bg-surface-primary text-text-primary">
      <Nav />

      <main className="flex-1">
        {/* Hero — type-only, asymmetric, generous */}
        <section className="mx-auto max-w-(--container-wide) px-6 md:px-12 pt-24 md:pt-32 pb-24 md:pb-32">
          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-12 md:col-span-9 lg:col-span-8">
              <p className="font-body text-sm text-text-secondary mb-8 inline-flex items-center gap-2">
                <span aria-hidden="true" className="signature-dot" />
                Draft assistance for US health-insurance appeals
              </p>
              <h1 className="font-display font-semibold text-display-lg md:text-display-xl lg:text-display-2xl leading-[1.05] tracking-tight text-text-primary">
                A denial is not the final answer.
              </h1>
              <dl className="mt-10 grid grid-cols-3 gap-0 max-w-prose">
                <div className="pr-4 sm:pr-6 text-center">
                  <dt className="font-display text-display-sm md:text-display-md font-semibold tracking-tight text-text-primary leading-none">
                    19%
                  </dt>
                  <dd className="mt-3 font-body text-sm leading-snug text-text-secondary">
                    of in-network claims denied (≈73M/yr on ACA)
                  </dd>
                </div>
                <div className="px-4 sm:px-6 border-l border-[color:var(--border-subtle)] text-center">
                  <dt className="font-display text-display-sm md:text-display-md font-semibold tracking-tight text-text-primary leading-none">
                    1 in 3
                  </dt>
                  <dd className="mt-3 font-body text-sm leading-snug text-text-secondary">
                    appeals succeed when patients file
                  </dd>
                </div>
                <div className="pl-4 sm:pl-6 border-l border-[color:var(--border-subtle)] text-center">
                  <dt className="font-display text-display-sm md:text-display-md font-semibold tracking-tight text-text-primary leading-none">
                    &lt;1%
                  </dt>
                  <dd className="mt-3 font-body text-sm leading-snug text-text-secondary">
                    of denials are ever appealed
                  </dd>
                </div>
              </dl>
              <p className="mt-10 max-w-prose font-body text-lg md:text-xl leading-snug text-text-secondary">
                Tell us what happened. We&apos;ll help you draft an appeal grounded in your story
                and the rules that protect you.
              </p>
              <div className="mt-12 flex flex-col sm:flex-row gap-3">
                <Link href="/appeal">
                  <Button>
                    Start a draft
                    <ArrowRightIcon size={16} />
                  </Button>
                </Link>
                <a href="#how-it-works">
                  <Button variant="secondary">How this works</Button>
                </a>
              </div>
              <p className="mt-8 font-body text-sm text-text-tertiary">
                Filing an appeal takes about thirty minutes. Most people we&apos;ve helped finish in one sitting.
              </p>
            </div>
          </div>
        </section>

        <hr className="hairline mx-auto max-w-(--container-wide) ml-6 md:ml-12 mr-6 md:mr-12" />

        {/* What this is / what this isn't — three calm columns of clarity */}
        <section
          id="what-this-is"
          className="mx-auto max-w-(--container-wide) px-6 md:px-12 py-24 md:py-32"
        >
          <div className="grid grid-cols-12 gap-12">
            <div className="col-span-12 md:col-span-4">
              <h2 className="font-display text-display-md font-semibold tracking-tight">
                What this is
              </h2>
              <p className="mt-6 font-body text-base leading-base text-text-secondary">
                A draft assistant. You share what happened — what was denied, why the insurer said no, what your
                doctor recommended. We turn it into an appeal draft you can read, edit, and file.
              </p>
            </div>
            <div className="col-span-12 md:col-span-4">
              <h2 className="font-display text-display-md font-semibold tracking-tight">
                What this is not
              </h2>
              <p className="mt-6 font-body text-base leading-base text-text-secondary">
                Not legal counsel. Not medical advice. Not a service that files anything for you. You, your doctor,
                an advocate — should read and fully understand every draft before it is filed.
              </p>
            </div>
            <div className="col-span-12 md:col-span-4">
              <h2 className="font-display text-display-md font-semibold tracking-tight">
                What we don&apos;t do
              </h2>
              <p className="mt-6 font-body text-base leading-base text-text-secondary">
                We don&apos;t store your medical records. We don&apos;t talk to your insurer. And though about half
                of all appeals win, we cannot promise yours will.
              </p>
            </div>
          </div>
        </section>

        <hr className="hairline mx-auto max-w-(--container-wide) ml-6 md:ml-12 mr-6 md:mr-12" />

        {/* How it works — three steps, hairline between, no numbered circles */}
        <section
          id="how-it-works"
          className="mx-auto max-w-(--container-wide) px-6 md:px-12 py-24 md:py-32"
        >
          <h2 className="font-display text-display-md md:text-display-lg font-semibold tracking-tight max-w-xl">
            Three steps. About thirty minutes.
          </h2>
          <ol className="mt-16 grid grid-cols-12 gap-12">
            <li className="col-span-12 md:col-span-4">
              <p className="font-body text-sm text-text-tertiary inline-flex items-center gap-2">
                <span aria-hidden="true" className="signature-dot" />
                Step one
              </p>
              <h3 className="mt-3 font-display text-display-sm font-semibold tracking-tight">
                Tell us what happened
              </h3>
              <p className="mt-3 font-body text-base leading-base text-text-secondary">
                Paste the denial letter, some surrounding clinical context and answer a few short questions. In
                your words and your doctor notes, if available
              </p>
            </li>
            <li className="col-span-12 md:col-span-4">
              <p className="font-body text-sm text-text-tertiary inline-flex items-center gap-2">
                <span aria-hidden="true" className="signature-dot" />
                Step two
              </p>
              <h3 className="mt-3 font-display text-display-sm font-semibold tracking-tight">
                We mirror it back
              </h3>
              <p className="mt-3 font-body text-base leading-base text-text-secondary">
                A short summary of what we heard, the rules that apply, and the strongest case we can make on
                your behalf — before any letter is drafted.
              </p>
            </li>
            <li className="col-span-12 md:col-span-4">
              <p className="font-body text-sm text-text-tertiary inline-flex items-center gap-2">
                <span aria-hidden="true" className="signature-dot" />
                Step three
              </p>
              <h3 className="mt-3 font-display text-display-sm font-semibold tracking-tight">
                You read and edit
              </h3>
              <p className="mt-3 font-body text-base leading-base text-text-secondary">
                The draft appears, sentence by sentence. You can change anything. When it sounds like you, you
                download it.
              </p>
            </li>
          </ol>
        </section>
      </main>

      <footer
        id="disclosure"
        className="mt-auto w-full border-t border-border-subtle bg-surface-primary"
      >
        <div className="mx-auto max-w-(--container-wide) px-6 md:px-12 py-12 grid grid-cols-12 gap-8">
          <div className="col-span-12 md:col-span-6">
            <Wordmark />
            <p className="mt-4 font-body text-sm text-text-tertiary max-w-md">
              Not legal or medical advice. Draft assistance only. A person should read every draft before
              you file anything.
            </p>
          </div>
          <div className="col-span-12 md:col-span-6 md:text-right">
            <Link
              href="/showcase"
              className="font-body text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              How this gets better over time
            </Link>
            <p className="mt-3 font-body text-sm text-text-tertiary">
              Built for the Google Cloud Rapid Agent Hackathon · Apache 2.0
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
