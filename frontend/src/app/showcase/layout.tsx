import "../styles/showcase.css";

export default function ShowcaseLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div data-theme="showcase-dark" className="showcase min-h-dvh">
      {children}
    </div>
  );
}
