import "../../styles/showcase.css";

/**
 * Showcase shell.
 * - `data-theme="dark"` remaps the global semantic tokens (surfaces/text/borders)
 *   to their dark values for shared chrome (Nav, Button, SettingsPanel) so it
 *   reads correctly on the cinematic background. Scoped to the showcase subtree;
 *   never touches `/appeal`.
 * - `.showcase` layers the bespoke `--sc-*` cinematic tokens + key-light on top.
 */
export default function ShowcaseLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div data-theme="dark" className="showcase min-h-dvh">
      {children}
    </div>
  );
}
