import { useState } from "react";

export default function Creator() {
  const [to,setTo]=useState(""); const [subject,setSubject]=useState(""); const [body,setBody]=useState("");
  const send = async () => {
    await fetch("/api/notify", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({to,subject,body})});
    alert("Queued");
  };
  return (
    <main style={{padding:"2rem",maxWidth:720,margin:"0 auto",fontFamily:"ui-sans-serif"}}>
      <h1>Creator — Outreach</h1>
      <p>Quick test: sends an email via Brevo through your API.</p>
      <div style={{display:"grid",gap:"0.75rem"}}>
        <input placeholder="Recipient email" value={to} onChange={e=>setTo(e.target.value)} />
        <input placeholder="Subject" value={subject} onChange={e=>setSubject(e.target.value)} />
        <textarea placeholder="Body" rows={6} value={body} onChange={e=>setBody(e.target.value)} />
        <button onClick={send}>Send</button>
      </div>
    </main>
  );
}