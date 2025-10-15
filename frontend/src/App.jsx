import React, { useState, useEffect } from 'react';
import Login from './pages/Login';
import CalendarPage from './pages/CalendarPage';
import AdminPanel from './pages/AdminPanel';
import axios from 'axios';
const API = axios.create({ baseURL: 'http://localhost:8000/api' , withCredentials: true});
export default function App(){
  const [token, setToken] = useState(localStorage.getItem('token')||null);
  const [role, setRole] = useState(localStorage.getItem('role')||null);
  useEffect(()=>{
    const req = API.interceptors.request.use(cfg=>{ if(token) cfg.headers.Authorization = `Bearer ${token}`; return cfg; });
    const res = API.interceptors.response.use(r=>r, async err=>{
      const original = err.config;
      if(err.response && err.response.status === 401 && !original._retry){
        original._retry = true;
        try{
          const r = await API.post('/auth/refresh');
          const newToken = r.data.access_token;
          setToken(newToken); localStorage.setItem('token', newToken);
          original.headers.Authorization = `Bearer ${newToken}`;
          return API(original);
        }catch(e){
          setToken(null); setRole(null); localStorage.clear(); return Promise.reject(e);
        }
      }
      return Promise.reject(err);
    });
    return ()=>{ API.interceptors.request.eject(req); API.interceptors.response.eject(res); };
  }, [token]);
  const onLogin = (t,r)=>{ localStorage.setItem('token', t); localStorage.setItem('role', r); setToken(t); setRole(r); };
  if(!token) return <Login onLogin={onLogin} />;
  return (<div className='app-root'><header className='app-header'><div className='brand'><div className='logo-placeholder'>sistemab.ru</div><h1>Календарь монтажников</h1></div><div className='header-controls'><span className='role'>Роль: {role}</span><button onClick={async ()=>{ try{ await API.post('/auth/logout'); }catch(e){} localStorage.clear(); setToken(null); setRole(null); }}>Выход</button></div></header><main className='app-main'><CalendarPage token={token} role={role} /><AdminPanel token={token} /></main></div>);
}
