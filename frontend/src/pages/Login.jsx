import React, { useState } from 'react';
import { login } from '../api';
export default function Login({ onLogin }){
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('adminpass');
  const [err, setErr] = useState(null);
  const submit = async (e) =>{
    e.preventDefault();
    try{
      const r = await login(username, password);
      const token = r.data.access_token;
      const payload = JSON.parse(atob(token.split('.')[1]));
      const role = payload.role;
      onLogin(token, role);
    }catch(e){
      setErr('Ошибка входа');
    }
  };
  return (<div style={{maxWidth:480, margin:'80px auto', padding:20, background:'#fff', borderRadius:8}}>
    <h2>Вход в систему</h2>
    <form onSubmit={submit}>
      <div style={{marginBottom:8}}><input value={username} onChange={e=>setUsername(e.target.value)} placeholder='Логин' style={{width:'100%', padding:8}}/></div>
      <div style={{marginBottom:8}}><input type='password' value={password} onChange={e=>setPassword(e.target.value)} placeholder='Пароль' style={{width:'100%', padding:8}}/></div>
      <div style={{display:'flex', gap:8}}><button className='btn' type='submit'>Войти</button><button className='btn secondary' type='button' onClick={()=>{ setUsername('admin'); setPassword('adminpass'); }}>Тест</button></div>
      {err && <div style={{color:'red', marginTop:8}}>{err}</div>}
    </form>
  </div>);
}
