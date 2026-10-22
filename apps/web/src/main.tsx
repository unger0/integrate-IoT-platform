import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

type Leitura={message_id:string;measured_at:string;measurement_name:string;value:number;unit:string};
const API='http://localhost:8000';
function App(){
 const [device,setDevice]=useState('solo-talhao07-02');
 const [readings,setReadings]=useState<Leitura[]>([]);
 const [status,setStatus]=useState('Escolha um dispositivo e consulte a telemetria.');
 async function load(){
  setStatus('Consultando API local...');
  try{
   const resp=await fetch(`${API}/api/v1/dispositivos/${encodeURIComponent(device)}/telemetria`);
   if(!resp.ok)throw new Error(`HTTP ${resp.status}`);
   const data=await resp.json(); setReadings(data.dados);setStatus(`${data.total_retorno} leitura(s) retornada(s)`);
  }catch(err){setStatus('API indisponível: '+String(err));setReadings([]);}
 }
 return <main><p className="eyebrow">UNIEVANGÉLICA · IoT</p><h1>Plataforma IoT Integrada</h1><p>Protótipo didático — somente consulta; autenticação e isolamento ainda pendentes.</p><section><label htmlFor="dev">Dispositivo</label><select id="dev" value={device} onChange={e=>setDevice(e.target.value)}><option value="solo-talhao07-02">Sensor de solo • Rural</option><option value="ar-centro-03">Estação de ar • Urbano</option></select><button onClick={load}>Consultar</button></section><p role="status">{status}</p><div className="wrap"><table><thead><tr><th>Instante da medição</th><th>Grandeza</th><th>Valor</th><th>Unidade</th></tr></thead><tbody>{readings.map((r,i)=><tr key={r.message_id+'-'+i}><td>{new Date(r.measured_at).toLocaleString('pt-BR')}</td><td>{r.measurement_name}</td><td>{r.value}</td><td>{r.unit}</td></tr>)}</tbody></table></div><small>Não é o painel de produção previsto em RF-APP-04/06.</small></main>
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
