import React, { useState } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'https://montaj-calendar.onrender.com/api';

export default function App() {
  const [msg, setMsg] = useState('');

  async function check() {
    const token = localStorage.getItem('idToken') || '';
    try {
      const r = await fetch(API_BASE + '/health', { headers: { Authorization: 'Bearer ' + token } });
      const j = await r.json();
      setMsg(JSON.stringify(j, null, 2));
    } catch (e) {
      setMsg('Ошибка: ' + e.message);
    }
  }

  return (
    <div style={{ padding: 20, fontFamily: 'Arial' }}>
      <h2>Montaj frontend (demo)</h2>
      <p>API: {API_BASE}</p>
      <button onClick={check}>Check API /health</button>
      <pre>{msg}</pre>
      <p>This frontend is minimal — integrate your React app and set REACT_APP_API_URL before build.</p>
    </div>
  );
}
