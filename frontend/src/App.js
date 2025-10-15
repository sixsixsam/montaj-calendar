import React, {useState} from 'react';
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
export default function App(){
  const [msg, setMsg] = useState('');
  async function check(){
    const token = localStorage.getItem('idToken') || '';
    const r = await fetch(API_BASE + '/health', { headers: { Authorization: 'Bearer ' + token } });
    const j = await r.json();
    setMsg(JSON.stringify(j));
  }
  return (<div style={{padding:20,fontFamily:'Arial'}}>
    <h2>Montaj frontend (demo)</h2>
    <p>API: {API_BASE}</p>
    <button onClick={check}>Check API /health</button>
    <pre>{msg}</pre>
    <p>This frontend is minimal — integrate your React app and set REACT_APP_API_URL before build.</p>
  </div>);
}
