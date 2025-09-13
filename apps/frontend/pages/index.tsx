import Link from "next/link";

export default function Home() {
  return (
    <main style={{padding:"3rem",maxWidth:900,margin:"0 auto",fontFamily:"ui-sans-serif"}}>
      <h1 style={{fontSize:"2.25rem", marginBottom:"0.5rem"}}>Dominion’s Ark</h1>
      <p style={{opacity:0.8}}>Elite multi-agent AI automation — orchestrated by Jarvis.</p>

      <section style={{marginTop:"2rem"}}>
        <h2>Status</h2>
        <ul>
          <li>API: <a href="/api/healthz">/api/healthz</a> (proxied)</li>
          <li>Control Panel (soon): <Link href="https://app.dominionhealing.org">app.dominionhealing.org</Link></li>
          <li>API Direct: <Link href="https://api.dominionhealing.org/healthz">api.dominionhealing.org/healthz</Link></li>
        </ul>
      </section>

      <section style={{marginTop:"2rem"}}>
        <h2>Content Creator</h2>
        <p>No more blank screen. Hook this to Jarvis flows next.</p>
        <Link href="/creator">Open Creator</Link>
      </section>
    </main>
  );
}