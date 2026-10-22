import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

// Exclusivamente LABORATÓRIO local: sem autenticação, RBAC, TLS nem isolamento autorizado.
const API = 'http://127.0.0.1:8000';
type View = 'visao' | 'dispositivos' | 'perfis' | 'historico';
type Device = {id:string;tenant_id:string;domain:string;site:string;area:string|null;profile_name:string|null;manufacturer:string|null;firmware:string|null};
type Profile = {name:string;domain:string;expected_interval_seconds:number};
type ProfileMeasure = {measurement_name:string;unit:string;minimum:number;maximum:number};
type ProfileDetail = {tenant_id:string;name:string;domain:string;expected_interval_seconds:number;medidas:ProfileMeasure[]};
type Reading = {message_id:string;measured_at:string;measurement_name:string;value:number;unit:string;quality:string;quality_reason:string|null};
type MeasureDraft = {grandeza:string;unidade:string;minimo:string;maximo:string};
type Notice = {text:string;kind:'ok'|'erro'} | null;
const starterMeasure = ():MeasureDraft => ({grandeza:'umidade_solo', unidade:'%', minimo:'0', maximo:'100'});

async function request<T>(path:string, options?:RequestInit):Promise<T> {
  let response:Response;
  try {
    response = await fetch(API+path, { ...options, headers: {'Content-Type':'application/json', ...options?.headers} });
  } catch {
    throw new Error('Não foi possível conectar à API. Verifique os contêineres Docker e a porta 8000.');
  }
  let result:unknown;
  try {result=await response.json();} catch {throw new Error(`Resposta inválida da API (HTTP ${response.status}).`);}
  if(!response.ok) {
    const obj = result as {detail?:string|unknown;erros?:string[]};
    const message = typeof obj?.detail==='string' ? obj.detail : Array.isArray(obj?.erros) ? obj.erros.join('; ') : `HTTP ${response.status}`;
    throw new Error(message);
  }
  return result as T;
}
const submitJson = <T,>(path:string, method:string, payload:unknown) => request<T>(path, { method, body:JSON.stringify(payload) });
const dateLabel = (raw:string) => new Date(raw).toLocaleString('pt-BR', {dateStyle:'short',timeStyle:'medium'});

function App() {
  const [view,setView]=useState<View>('visao');
  const [tenantInput,setTenantInput]=useState('coop-cerrado');
  const [tenant,setTenant]=useState('coop-cerrado');
  const [apiHealthy,setApiHealthy]=useState(false);
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState<Notice>(null);
  const [domains,setDomains]=useState<string[]>([]);
  const [profiles,setProfiles]=useState<Profile[]>([]);
  const [devices,setDevices]=useState<Device[]>([]);
  const [selectedDevice,setSelectedDevice]=useState('');
  const [readings,setReadings]=useState<Reading[]>([]);
  const [loadingHistory,setLoadingHistory]=useState(false);
  const [qualityFilter,setQualityFilter]=useState('todas');
  const [deviceSearch,setDeviceSearch]=useState('');
  const [profileDetail,setProfileDetail]=useState<ProfileDetail|null>(null);
  const [domainName,setDomainName]=useState('');
  const [deviceForm,setDeviceForm]=useState({id:'',dominio:'',site:'',area:''});
  const [profileName,setProfileName]=useState('');
  const [profileDomain,setProfileDomain]=useState('');
  const [profileInterval,setProfileInterval]=useState('600');
  const [profileMeasures,setProfileMeasures]=useState<MeasureDraft[]>([starterMeasure()]);
  const [bindDevice,setBindDevice]=useState('');
  const [bindProfile,setBindProfile]=useState('');
  const [refreshCount,setRefreshCount]=useState(0);

  const refresh=useCallback(async()=>{
    setBusy(true);
    try {
      const q=encodeURIComponent(tenant);
      const [d,p,dev]=await Promise.all([
        request<{dominios:string[]}>(`/api/v1/catalogo/dominios?inquilino=${q}`),
        request<{perfis:Profile[]}>(`/api/v1/catalogo/perfis?inquilino=${q}`),
        request<{dispositivos:Device[]}>(`/api/v1/dispositivos?inquilino=${q}&limite=500`)
      ]);
      setDomains(d.dominios);setProfiles(p.perfis);setDevices(dev.dispositivos);
      setSelectedDevice(old=>dev.dispositivos.some(item=>item.id===old)?old:(dev.dispositivos[0]?.id||''));
      setBindDevice(old=>dev.dispositivos.some(item=>item.id===old)?old:(dev.dispositivos[0]?.id||''));
      setApiHealthy(true);
    } catch(e) {
      setApiHealthy(false);setDomains([]);setProfiles([]);setDevices([]);setReadings([]);
      setNotice({kind:'erro',text:String((e as Error).message||e)});
    } finally {setBusy(false);}
  },[tenant]);
  useEffect(()=>{void refresh();},[refresh,refreshCount]);

  const loadReadings=useCallback(async()=>{
    if(!selectedDevice){setReadings([]);return;}
    setLoadingHistory(true);
    try {
      const result=await request<{dados:Reading[]}>(`/api/v1/dispositivos/${encodeURIComponent(selectedDevice)}/telemetria?limite=500`);
      setReadings(result.dados);
    } catch(e) {setReadings([]);setNotice({kind:'erro',text:String((e as Error).message||e)});}
    finally{setLoadingHistory(false);}
  },[selectedDevice]);
  useEffect(()=>{void loadReadings();},[loadReadings,refreshCount]);

  const pickedDevice=devices.find(d=>d.id===selectedDevice);
  const bindPicked=devices.find(d=>d.id===bindDevice);
  const bindOptions=profiles.filter(p=>p.domain===bindPicked?.domain);
  const chosenDomain=domains.includes(profileDomain)?profileDomain:(domains[0]||'');
  const chosenDeviceDomain=domains.includes(deviceForm.dominio)?deviceForm.dominio:(domains[0]||'');
  const suspicious=readings.filter(r=>r.quality==='suspeita').length;
  const conforming=readings.filter(r=>r.quality==='conforme').length;
  const filteredReadings=readings.filter(r=>qualityFilter==='todas'||r.quality===qualityFilter);
  const filteredDevices=devices.filter(d=>`${d.id} ${d.site} ${d.domain} ${d.profile_name||''}`.toLowerCase().includes(deviceSearch.toLowerCase()));
  const grouped=useMemo(()=>{
    const result = new Map<string,Reading>();
    for(const r of [...readings].reverse()) result.set(r.measurement_name,r);
    return [...result.values()];
  },[readings]);

  async function action(work:()=>Promise<void>, success:string) {
    setBusy(true);setNotice(null);
    try {await work();setNotice({kind:'ok',text:success});setRefreshCount(i=>i+1);}
    catch(e){setNotice({kind:'erro',text:String((e as Error).message||e)});}
    finally{setBusy(false);}
  }
  function addDomain(e:React.FormEvent){e.preventDefault();if(!domainName.trim())return;
    void action(async()=>{await submitJson('/api/v1/catalogo/dominios','POST',{inquilino:tenant,nome:domainName.trim()});setDomainName('');},'Domínio cadastrado ou já existente.');
  }
  function addDevice(e:React.FormEvent){e.preventDefault();if(!deviceForm.id.trim()||!deviceForm.site.trim()||!chosenDeviceDomain)return;
    void action(async()=>{await submitJson('/api/v1/dispositivos','POST',{id:deviceForm.id.trim(),inquilino:tenant,dominio:chosenDeviceDomain,site:deviceForm.site.trim(),area:deviceForm.area.trim()||null});setSelectedDevice(deviceForm.id.trim());setDeviceForm({id:'',dominio:'',site:'',area:''});},'Dispositivo cadastrado.');
  }
  function updateMeasure(index:number,part:Partial<MeasureDraft>){setProfileMeasures(list=>list.map((m,i)=>i===index?{...m,...part}:m));}
  function addProfile(e:React.FormEvent){e.preventDefault();if(!profileName.trim()||!chosenDomain)return;
    void action(async()=>{
      await submitJson('/api/v1/catalogo/perfis','POST',{
        inquilino:tenant,nome:profileName.trim(),dominio:chosenDomain,
        intervalo_esperado_segundos:Number(profileInterval),
        medidas:profileMeasures.map(m=>({grandeza:m.grandeza.trim(),unidade:m.unidade.trim(),minimo:Number(m.minimo),maximo:Number(m.maximo)}))
      });setProfileName('');setProfileMeasures([starterMeasure()]);
    },'Perfil criado. Agora você pode vinculá-lo a um dispositivo.');
  }
  function linkProfile(e:React.FormEvent){e.preventDefault();const chosen=bindOptions.find(p=>p.name===bindProfile)||bindOptions[0];if(!chosen||!bindDevice)return;
    void action(async()=>{await submitJson(`/api/v1/dispositivos/${encodeURIComponent(bindDevice)}/perfil`,'PUT',{inquilino:tenant,perfil:chosen.name});},`Perfil ${chosen.name} vinculado ao dispositivo ${bindDevice}.`);
  }
  function inspectProfile(p:Profile){
    setProfileDetail(null);void request<ProfileDetail>(`/api/v1/catalogo/perfis/${encodeURIComponent(tenant)}/${encodeURIComponent(p.name)}`)
      .then(setProfileDetail).catch(e=>setNotice({kind:'erro',text:String(e)}));
  }
  const label:Record<View,string>={visao:'Visão geral',dispositivos:'Dispositivos',perfis:'Perfis',historico:'Histórico'};

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">◈</div><div><strong>Integra IoT</strong><small>PLATAFORMA · LAB</small></div></div>
      <div className="nav-label">GERENCIAMENTO</div>
      <nav aria-label="Navegação principal">
        {(['visao','dispositivos','perfis','historico'] as View[]).map((v,i)=><button key={v} className={`nav-link ${view===v?'active':''}`} onClick={()=>setView(v)}><span aria-hidden="true">{['▦','▤','◇','◷'][i]}</span>{label[v]}</button>)}
      </nav>
      <div className="sidebar-bottom"><div className="sidebar-status"><span className={`status-dot ${apiHealthy?'online':'offline'}`}/>{apiHealthy?'API central conectada':'API indisponível'}</div><small>v0.3.0 · Arch Linux</small></div>
    </aside>

    <main className="workspace">
      <header className="topbar"><div><span className="eyebrow">UNIEVANGÉLICA / INTERNET DAS COISAS</span><h1>{label[view]}</h1></div>
        <div className="top-actions"><button className="button secondary" disabled={busy} onClick={()=>setRefreshCount(n=>n+1)}>↻ Atualizar</button><a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="button outline">Swagger ↗</a></div>
      </header>
      <div className="lab-warning" role="note"><span aria-hidden="true">⚠</span><div><strong>Ambiente didático local</strong><span>Sem login, autenticação de dispositivos ou isolamento seguro entre organizações. Não exponha à internet nem insira dados reais.</span></div></div>
      <div className="tenantbar"><div><label htmlFor="tenant">Organização (inquilino)</label><p>Filtro didático de dados. Não é autenticação.</p></div><form onSubmit={e=>{e.preventDefault();if(tenantInput.trim()){setProfileDetail(null);setReadings([]);setTenant(tenantInput.trim());}}}><input id="tenant" value={tenantInput} onChange={e=>setTenantInput(e.target.value)} placeholder="coop-cerrado" required/><button className="button primary" type="submit">Aplicar</button></form></div>
      {notice&&<div className={`notice ${notice.kind}`} role="status"><span>{notice.kind==='ok'?'✓':'!'}</span>{notice.text}<button aria-label="Fechar mensagem" onClick={()=>setNotice(null)}>×</button></div>}
      {view==='visao'&&<>
        <div className="hero"><div><div className="kicker">CENTRAL DE MONITORAMENTO</div><h2>Uma visão integrada de dispositivos e leituras.</h2><p>Informações obtidas da API da plataforma, com dados da organização <strong>{tenant}</strong>.</p></div><div className="hero-graphic" aria-hidden="true"><span>◉</span><i/><i/><i/></div></div>
        <div className="metrics">
          <div className="metric"><span>Dispositivos cadastrados</span><strong>{devices.length}</strong><small>Até 500 exibidos nesta consulta</small></div>
          <div className="metric"><span>Perfis configurados</span><strong>{profiles.length}</strong><small>Domínios: {domains.length}</small></div>
          <div className="metric"><span>Leituras suspeitas</span><strong className="orange">{suspicious}</strong><small>No histórico do dispositivo selecionado</small></div>
          <div className="metric"><span>Leituras conformes</span><strong className="green">{conforming}</strong><small>No histórico do dispositivo selecionado</small></div>
        </div>
        <div className="two-columns">
          <section className="panel"><div className="panel-head"><div><h3>Dispositivos recentes</h3><p>Inventário desta organização</p></div><button className="linklike" onClick={()=>setView('dispositivos')}>Ver todos →</button></div>
            {devices.length===0?<div className="empty">Nenhum dispositivo encontrado para {tenant}.</div>:<div className="stack">{devices.slice(0,6).map(d=><button className="device-mini" key={d.id} onClick={()=>{setSelectedDevice(d.id);setView('historico');}}><span className="mini-icon">⌁</span><span><strong>{d.id}</strong><small>{d.site} · {d.domain}</small></span><span className="mini-arrow">→</span></button>)}</div>}
          </section>
          <section className="panel"><div className="panel-head"><div><h3>Últimas grandezas</h3><p>{selectedDevice||'Selecione um dispositivo'}</p></div><button className="linklike" onClick={()=>setView('historico')}>Histórico →</button></div>
            {grouped.length===0?<div className="empty">Nenhuma medição disponível para este dispositivo.</div>:<div className="stack">{grouped.slice(0,6).map(m=><div className="reading-mini" key={m.measurement_name}><div><strong>{m.measurement_name}</strong><small>{dateLabel(m.measured_at)}</small></div><div className="number-value">{m.value.toLocaleString('pt-BR')} <small>{m.unit}</small><span className={`tag ${m.quality}`}>{m.quality==='suspeita'?'Suspeita':m.quality==='conforme'?'Conforme':'Não avaliada'}</span></div></div>)}</div>}
          </section>
        </div>
      </>}

      {view==='dispositivos'&&<>
        <div className="two-columns wide-left">
          <section className="panel"><div className="panel-head"><div><h3>Inventário</h3><p>{devices.length} dispositivos encontrados</p></div><input className="search" value={deviceSearch} onChange={e=>setDeviceSearch(e.target.value)} placeholder="Buscar identificador, local..." aria-label="Filtrar dispositivos"/></div>
            <div className="table-wrap"><table><thead><tr><th>Identificador</th><th>Domínio</th><th>Local / área</th><th>Perfil</th><th/></tr></thead><tbody>{filteredDevices.map(d=><tr key={d.id}><td><strong>{d.id}</strong></td><td>{d.domain}</td><td>{d.site}<small className="table-sub">{d.area||'Sem área'}</small></td><td><span className={`tag ${d.profile_name?'conforme':'nao_avaliada'}`}>{d.profile_name||'Sem perfil'}</span></td><td><button className="table-action" onClick={()=>{setSelectedDevice(d.id);setView('historico');}}>Histórico →</button></td></tr>)}</tbody></table></div>
            {filteredDevices.length===0&&<div className="empty">Nenhum dispositivo corresponde à busca.</div>}
          </section>
          <section className="panel"><h3>Cadastrar dispositivo</h3><p className="subheading">Cadastro básico, sem credenciais.</p><form className="field-stack" onSubmit={addDevice}>
            <label>Identificador<input required minLength={1} value={deviceForm.id} onChange={e=>setDeviceForm(f=>({...f,id:e.target.value}))} placeholder="sensor-exemplo-01"/></label>
            <label>Domínio<select required value={chosenDeviceDomain} onChange={e=>setDeviceForm(f=>({...f,dominio:e.target.value}))}>{domains.length===0?<option value="">Cadastre um domínio</option>:domains.map(d=><option key={d}>{d}</option>)}</select></label>
            <label>Local<input required value={deviceForm.site} onChange={e=>setDeviceForm(f=>({...f,site:e.target.value}))} placeholder="fazenda-boa-vista"/></label>
            <label>Área (opcional)<input value={deviceForm.area} onChange={e=>setDeviceForm(f=>({...f,area:e.target.value}))} placeholder="talhao-07"/></label>
            <button disabled={busy||domains.length===0} type="submit" className="button primary fill">Cadastrar dispositivo</button>
          </form></section>
        </div>
        <section className="panel compact"><h3>Vincular perfil existente</h3><p className="subheading">Escolha um dispositivo e um perfil do mesmo domínio. Leituras antigas não serão reclassificadas.</p>
          <form className="inline-form" onSubmit={linkProfile}><label>Dispositivo<select value={bindDevice} onChange={e=>{setBindDevice(e.target.value);setBindProfile('');}}>{devices.map(d=><option value={d.id} key={d.id}>{d.id}</option>)}</select></label><label>Perfil compatível<select value={bindOptions.some(p=>p.name===bindProfile)?bindProfile:(bindOptions[0]?.name||'')} onChange={e=>setBindProfile(e.target.value)}>{bindOptions.length===0?<option value="">Nenhum perfil disponível</option>:bindOptions.map(p=><option key={p.name} value={p.name}>{p.name}</option>)}</select></label><button className="button primary" disabled={busy||!bindDevice||!bindOptions.length} type="submit">Vincular perfil</button></form>
        </section>
      </>}

      {view==='perfis'&&<>
        <div className="two-columns wide-left">
          <section className="panel"><div className="panel-head"><div><h3>Perfis cadastrados</h3><p>Tipos de sensores configurados sem alteração no código</p></div><span className="count-pill">{profiles.length}</span></div>
            <div className="stack">{profiles.length===0?<div className="empty">Nenhum perfil nesta organização.</div>:profiles.map(p=><button key={p.name} className="profile-item" onClick={()=>inspectProfile(p)}><div className="profile-icon">◇</div><span><strong>{p.name}</strong><small>{p.domain} · a cada {p.expected_interval_seconds}s</small></span><span className="mini-arrow">Detalhes →</span></button>)}</div>
            {profileDetail&&<div className="detail"><div className="panel-head"><h4>{profileDetail.name}</h4><button className="table-action" onClick={()=>setProfileDetail(null)}>Fechar</button></div><p>Domínio: {profileDetail.domain} · Intervalo: {profileDetail.expected_interval_seconds}s</p><table><thead><tr><th>Grandeza</th><th>Unidade</th><th>Mín.</th><th>Máx.</th></tr></thead><tbody>{profileDetail.medidas.map(m=><tr key={m.measurement_name}><td>{m.measurement_name}</td><td>{m.unit}</td><td>{m.minimum}</td><td>{m.maximum}</td></tr>)}</tbody></table></div>}
          </section>
          <section className="panel"><h3>Adicionar domínio</h3><p className="subheading">Ex.: agricultura, ambiente, recursos_hidricos.</p><form className="field-stack" onSubmit={addDomain}><label>Nome do domínio<input required value={domainName} onChange={e=>setDomainName(e.target.value)} placeholder="recursos_hidricos"/></label><button className="button outline fill" type="submit" disabled={busy}>Adicionar domínio</button></form></section>
        </div>
        <section className="panel"><h3>Criar perfil de dispositivo</h3><p className="subheading">Defina grandezas e faixas aceitas pelo sensor. Um valor fora da faixa será armazenado como suspeito.</p>
          <form className="field-stack" onSubmit={addProfile}>
            <div className="field-grid"><label>Nome do perfil<input required value={profileName} onChange={e=>setProfileName(e.target.value)} placeholder="sensor-solo-v1"/></label><label>Domínio<select required value={chosenDomain} onChange={e=>setProfileDomain(e.target.value)}>{domains.length===0?<option value="">Cadastre domínio antes</option>:domains.map(d=><option key={d}>{d}</option>)}</select></label><label>Intervalo esperado (segundos)<input type="number" min="1" max="2592000" required value={profileInterval} onChange={e=>setProfileInterval(e.target.value)}/></label></div>
            <div className="panel-head measure-header"><h4>Grandezas medidas</h4><button className="button secondary" type="button" disabled={profileMeasures.length>=50} onClick={()=>setProfileMeasures(list=>[...list,{grandeza:'',unidade:'',minimo:'0',maximo:'100'}])}>+ Adicionar grandeza</button></div>
            {profileMeasures.map((m,i)=><div className="measure-row" key={i}><label>Grandeza<input required value={m.grandeza} onChange={e=>updateMeasure(i,{grandeza:e.target.value})} placeholder="umidade_solo"/></label><label>Unidade<input required value={m.unidade} onChange={e=>updateMeasure(i,{unidade:e.target.value})} placeholder="%"/></label><label>Mínimo<input required type="number" step="any" value={m.minimo} onChange={e=>updateMeasure(i,{minimo:e.target.value})}/></label><label>Máximo<input required type="number" step="any" value={m.maximo} onChange={e=>updateMeasure(i,{maximo:e.target.value})}/></label><button className="remove-measure" aria-label="Remover grandeza" title="Remover grandeza" type="button" disabled={profileMeasures.length===1} onClick={()=>setProfileMeasures(items=>items.filter((_,j)=>j!==i))}>×</button></div>)}
            <div className="align-right"><button className="button primary" disabled={busy||!domains.length} type="submit">Salvar novo perfil</button></div>
          </form>
        </section>
      </>}

      {view==='historico'&&<>
        <section className="panel"><div className="panel-head"><div><h3>Telemetria do dispositivo</h3><p>Até 500 medições mais recentes, ordenadas por horário de medição</p></div><button disabled={loadingHistory} className="button secondary" onClick={()=>void loadReadings()}>↻ Atualizar leituras</button></div>
          <div className="filters"><label>Dispositivo<select value={selectedDevice} onChange={e=>setSelectedDevice(e.target.value)}>{devices.length===0?<option value="">Sem dispositivos</option>:devices.map(d=><option value={d.id} key={d.id}>{d.id}</option>)}</select></label><label>Classificação<select value={qualityFilter} onChange={e=>setQualityFilter(e.target.value)}><option value="todas">Todas</option><option value="conforme">Conforme</option><option value="suspeita">Suspeita</option><option value="nao_avaliada">Não avaliada</option></select></label><div className="filter-info">{pickedDevice?.site||'—'} · {pickedDevice?.domain||'—'}</div></div>
          <div className="metrics three"><div className="metric"><span>Leituras retornadas</span><strong>{readings.length}</strong></div><div className="metric"><span>Conformes</span><strong className="green">{conforming}</strong></div><div className="metric"><span>Suspeitas</span><strong className="orange">{suspicious}</strong></div></div>
          <div className="table-wrap"><table><thead><tr><th>Horário da medição</th><th>Grandeza</th><th>Valor</th><th>Qualidade</th><th>Motivo</th></tr></thead><tbody>{filteredReadings.map((r,i)=><tr key={r.message_id+'-'+r.measurement_name+'-'+i}><td>{dateLabel(r.measured_at)}</td><td><strong>{r.measurement_name}</strong></td><td>{r.value.toLocaleString('pt-BR')} {r.unit}</td><td><span className={`tag ${r.quality}`}>{r.quality==='conforme'?'Conforme':r.quality==='suspeita'?'Suspeita':'Não avaliada'}</span></td><td className="muted">{r.quality_reason||'—'}</td></tr>)}</tbody></table></div>
          {filteredReadings.length===0&&<div className="empty">{loadingHistory?'Buscando leituras...':'Nenhuma medição para o filtro selecionado.'}</div>}
          <p className="footnote">O filtro de qualidade é aplicado às medições retornadas. Não constitui consulta paginada de todo o banco.</p>
        </section>
      </>}
      <footer>Plataforma IoT Integrada · Laboratório acadêmico · v0.3.0 · Dados sintéticos</footer>
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
