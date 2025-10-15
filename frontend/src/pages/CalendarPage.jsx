import React, { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import { getCalendar, getWorkers, getProjects, createAssignment, listAssignments, deleteAssignment } from '../api';
function formatDay(d){ return dayjs(d).format('DD'); }
export default function CalendarPage({ token, role }){
  const [from, setFrom] = useState(dayjs().startOf('month').format('YYYY-MM-DD'));
  const [to, setTo] = useState(dayjs().endOf('month').format('YYYY-MM-DD'));
  const [data, setData] = useState(null);
  const [workers, setWorkers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [modal, setModal] = useState(null); // {date, projectId, selected: Set, assignmentsMap}
  useEffect(()=>{ fetchAll(); }, [from,to]);
  async function fetchAll(){
    try{
      const r = await getCalendar(from,to,token); setData(r.data);
      const w = await getWorkers(token); setWorkers(w.data);
      const p = await getProjects(token); setProjects(p.data);
      const a = await listAssignments(token, { from_date: from, to_date: to });
      const map = {};
      a.data.forEach(item=>{ if(!map[item.worker_id]) map[item.worker_id]=[]; map[item.worker_id].push(item); });
      setAssignmentsMap(map);
    }catch(e){ console.error(e); }
  }
  const [assignmentsMap, setAssignmentsMap] = useState({});
  function openEditor(date, projectName, projectId){
    const selected = new Set();
    for(const wid in assignmentsMap){
      const items = assignmentsMap[wid] || [];
      items.forEach(it=>{ if(it.project_id === projectId && it.start_date <= date && it.end_date >= date){ selected.add(Number(wid)); }});
    }
    setModal({ date, projectName, projectId, selected });
  }
  async function toggleWorker(w, checked){
    if(!modal) return;
    const date = modal.date;
    const pid = modal.projectId;
    if(checked){
      const items = assignmentsMap[w.id] || [];
      const hasOther = items.some(it => it.start_date <= date && it.end_date >= date && it.project_id !== pid);
      if(hasOther){
        if(!confirm(`${w.name} уже назначен в другой проект в этот день. Продолжить?`)) return;
      }
      await createAssignment(token, { project_id: pid, worker_id: w.id, start_date: date, end_date: date, work_type: null });
    } else {
      const items = assignmentsMap[w.id] || [];
      for(const it of items){
        if(it.project_id === pid && it.start_date <= date && it.end_date >= date){
          await deleteAssignment(token, it.id);
        }
      }
    }
    await fetchAll();
    const newSel = new Set(modal.selected);
    if(checked) newSel.add(w.id); else newSel.delete(w.id);
    setModal({...modal, selected: newSel});
  }
  if(!data) return <div className='calendar-wrap'>Загрузка...</div>;
  return (<div className='calendar-wrap'>
    <div className='controls'>
      <label>С <input type='date' value={from} onChange={e=>setFrom(e.target.value)} /></label>
      <label>По <input type='date' value={to} onChange={e=>setTo(e.target.value)} /></label>
      <button className='btn' onClick={()=>fetchAll()}>Обновить</button>
    </div>
    <div style={{overflow:'auto'}}>
      <table className='grid'>
        <thead><tr><th className='fixed-col'>Проект / Дата</th>{data.dates.map(d => <th key={d}>{formatDay(d)}</th>)}</tr></thead>
        <tbody>
          {data.rows.map(row => (
            <tr key={row.worker_id}>
              <td className='fixed-col'>{row.worker_name}</td>
              {data.dates.map(d => {
                const cell = row.cells[d];
                const projectName = cell?.project || '';
                const pid = projects.find(p=>p.name===projectName)?.id || null;
                return (<td key={d} className={'cell '+(cell? 'filled':'empty')} onDoubleClick={()=>{ if(role==='admin' && pid) openEditor(d, projectName, pid); }} title={cell? cell.work_type || projectName : ''}>{cell? (cell.work_type? cell.work_type : projectName): ''}</td>);
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    {modal && <><div className='overlay' onClick={()=>setModal(null)}></div><div className='modal'><h3>Назначить монтажников</h3><div className='small'>Дата: {modal.date} | Проект: {modal.projectName}</div><div style={{marginTop:12, maxHeight:300, overflow:'auto'}}>{workers.map(w=>{const items = assignmentsMap[w.id] || []; const hasOther = items.some(it=> it.start_date <= modal.date && it.end_date >= modal.date && it.project_id !== modal.projectId); const checked = modal.selected.has(w.id); return (<div key={w.id} style={{display:'flex', alignItems:'center', justifyContent:'space-between', padding:6}}><label><input type='checkbox' checked={checked} disabled={!w.active} onChange={e=>toggleWorker(w, e.target.checked)} /> {w.name} {!w.active && '(уволен)'} </label>{hasOther && <span className='warn'>⚠ занят(а) в другой задаче</span>}</div>); })}</div><div style={{marginTop:12, textAlign:'right'}}><button className='btn secondary' onClick={()=>setModal(null)}>Закрыть</button></div></div></>}</div>);
}
