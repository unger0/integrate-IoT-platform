import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

// Laboratório: autenticação JWT demonstrativa OPCIONAL; OIDC, MFA e TLS continuam ausentes.
const API = 'http://127.0.0.1:8000';
let demoAccessToken = ''; // somente memória volátil da aba; NÃO persiste em storage
type View = 'visao' | 'dispositivos' | 'perfis' | 'historico' | 'alarmes' | 'operacao' | 'observabilidade';
type Device = {id:string;tenant_id:string;domain:string;site:string;area:string|null;profile_name:string|null;manufacturer:string|null;firmware:string|null};
type DeviceHealth = {id:string;domain:string;site:string;area:string|null;profile_name:string|null;expected_interval_seconds:number|null;last_measured_at:string|null;estado:'em_dia'|'atrasado'|'sem_dados'|'sem_perfil'|'relogio_inconsistente';idade_segundos:number|null;tolerancia_segundos:number|null};
type ObsSummary = {inquilino:string;mensagens_persistidas:number;ultima_recepcao:string|null;classificacoes:Record<'conforme'|'suspeita'|'nao_avaliada',number>;alarmes_abertos:number;aviso:string};
type Profile = {name:string;domain:string;expected_interval_seconds:number};
type ProfileMeasure = {measurement_name:string;unit:string;minimum:number;maximum:number};
type ProfileDetail = {tenant_id:string;name:string;domain:string;expected_interval_seconds:number;medidas:ProfileMeasure[]};
type Reading = {message_id:string;measured_at:string;measurement_name:string;value:number;unit:string;quality:string;quality_reason:string|null};
type MeasureDraft = {grandeza:string;unidade:string;minimo:string;maximo:string};
type Rule = {id:number;name:string;device_id:string;measurement_name:string;unit:string;operator:string;threshold:number;severity:string;enabled:boolean;created_at:string};
type Alarm = {id:number;device_id:string;rule_name:string;measurement_name:string;operator:string;threshold:number;last_value:number;unit:string;severity:string;status:'ativo'|'reconhecido'|'resolvido';occurrences:number;last_measured_at:string;resolved_reason:string|null};
type Notice = {text:string;kind:'ok'|'erro'} | null;
type AuthMode = 'verificando'|'aberto'|'jwt'|'offline';
class ApiHttpError extends Error { constructor(readonly status:number, message:string) { super(message); this.name='ApiHttpError'; } }
const starterMeasure = ():MeasureDraft => ({grandeza:'umidade_solo', unidade:'%', minimo:'0', maximo:'100'});

async function request<T>(path:string, options?:RequestInit):Promise<T> {
  let response:Response;
  try {
    response = await fetch(API+path, { ...options, headers: {'Content-Type':'application/json', ...(demoAccessToken ? {'Authorization':`Bearer ${demoAccessToken}`} : {}), ...options?.headers} });
  } catch {
    throw new Error('Não foi possível conectar à API. Verifique os contêineres Docker e a porta 8000.');
  }
  let result:unknown;
  try {result=await response.json();} catch {throw new Error(`Resposta inválida da API (HTTP ${response.status}).`);}
  if(!response.ok) {
    const obj = result as {detail?:string|unknown;erros?:string[]};
    const message = typeof obj?.detail==='string' ? obj.detail : Array.isArray(obj?.erros) ? obj.erros.join('; ') : `HTTP ${response.status}`;
    throw new ApiHttpError(response.status, message);
  }
  return result as T;
}
const submitJson = <T,>(path:string, method:string, payload:unknown) => request<T>(path, { method, body:JSON.stringify(payload) });
const dateLabel = (raw:string) => new Date(raw).toLocaleString('pt-BR', {dateStyle:'short',timeStyle:'medium'});

function App() {
  const [view,setView]=useState<View>('visao');
  const [tokenInput,setTokenInput]=useState('');
  const [authMode,setAuthMode]=useState<AuthMode>('verificando');
  const [tokenActive,setTokenActive]=useState(false);
  const demoAuth=authMode==='jwt';
  useEffect(()=>{
    let active=true;
    void request<{modo_protegido_demo:boolean}>('/health')
      .then(h=>{if(active)setAuthMode(h.modo_protegido_demo?'jwt':'aberto');})
      .catch(()=>{if(active)setAuthMode('offline');});
    return ()=>{active=false;};
  },[]);
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
  const [rules,setRules]=useState<Rule[]>([]);
  const [alarms,setAlarms]=useState<Alarm[]>([]);
  const [deviceHealth,setDeviceHealth]=useState<DeviceHealth[]>([]);
  const [calculatedAt,setCalculatedAt]=useState('');
  const [obsSummary,setObsSummary]=useState<ObsSummary|null>(null);
  const [alarmFilter,setAlarmFilter]=useState('abertos');
  const [ruleForm,setRuleForm]=useState({nome:'',dispositivo:'',grandeza:'umidade_solo',unidade:'%',operador:'maior_que',limite:'80',severidade:'alta'});
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
      const [d,p,dev,rr,aa,op,ob]=await Promise.all([
        request<{dominios:string[]}>(`/api/v1/catalogo/dominios?inquilino=${q}`),
        request<{perfis:Profile[]}>(`/api/v1/catalogo/perfis?inquilino=${q}`),
        request<{dispositivos:Device[]}>(`/api/v1/dispositivos?inquilino=${q}&limite=500`),
        request<{regras:Rule[]}>(`/api/v1/regras?inquilino=${q}`),
        request<{alarmes:Alarm[]}>(`/api/v1/alarmes?inquilino=${q}&limite=200`),
        request<{dispositivos:DeviceHealth[];calculado_em:string}>(`/api/v1/operacao/dispositivos?inquilino=${q}&limite=500`),
        request<ObsSummary>(`/api/v1/observabilidade/resumo?inquilino=${q}`).catch(() => null)
      ]);
      setDomains(d.dominios);setProfiles(p.perfis);setDevices(dev.dispositivos);setRules(rr.regras);setAlarms(aa.alarmes);setDeviceHealth(op.dispositivos);setCalculatedAt(op.calculado_em);setObsSummary(ob);
      setSelectedDevice(old=>dev.dispositivos.some(item=>item.id===old)?old:(dev.dispositivos[0]?.id||''));
      setBindDevice(old=>dev.dispositivos.some(item=>item.id===old)?old:(dev.dispositivos[0]?.id||''));
      setApiHealthy(true);
    } catch(e) {
      const status=e instanceof ApiHttpError ? e.status : null;
      setApiHealthy(status===401||status===403);
      setDomains([]);setProfiles([]);setDevices([]);setReadings([]);setRules([]);setAlarms([]);setDeviceHealth([]);setCalculatedAt('');setObsSummary(null);
      if(status===401&&demoAuth){
        demoAccessToken='';setTokenActive(false);
        setNotice({kind:'erro',text:'Token ausente, inválido ou expirado. Gere ou copie novamente o token do laboratório.'});
      } else if(status===403){
        setNotice({kind:'erro',text:'Token recebido, mas sem permissão para consultar esta organização.'});
      } else {
        setNotice({kind:'erro',text:String((e as Error).message||e)});
      }
    } finally {setBusy(false);}
  },[tenant,demoAuth]);
  useEffect(()=>{
    if(authMode==='verificando'||authMode==='offline'||(demoAuth&&!tokenActive))return;
    void refresh();
  },[refresh,refreshCount,authMode,demoAuth,tokenActive]);

  const loadReadings=useCallback(async()=>{
    if(!selectedDevice){setReadings([]);return;}
    setLoadingHistory(true);
    try {
      const result=await request<{dados:Reading[]}>(`/api/v1/dispositivos/${encodeURIComponent(selectedDevice)}/telemetria?limite=500`);
      setReadings(result.dados);
    } catch(e) {setReadings([]);setNotice({kind:'erro',text:String((e as Error).message||e)});}
    finally{setLoadingHistory(false);}
  },[selectedDevice]);
  useEffect(()=>{
    if(authMode==='verificando'||authMode==='offline'||(demoAuth&&!tokenActive))return;
    void loadReadings();
  },[loadReadings,refreshCount,authMode,demoAuth,tokenActive]);

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
  async function submitToken(event:React.FormEvent) {
    event.preventDefault();
    const candidate=tokenInput.trim();
    if(!candidate){setNotice({kind:'erro',text:'Cole um token JWT antes de continuar.'});return;}
    setBusy(true);setNotice(null);
    demoAccessToken=candidate;
    try {
      const identity=await request<{autenticado:boolean;inquilino:string;papel:string}>('/api/v1/identidade');
      if(!identity.autenticado||!identity.inquilino)throw new Error('Token sem organização identificada.');
      setTenant(identity.inquilino);setTenantInput(identity.inquilino);
      setTokenActive(true);setTokenInput('');
      setNotice({kind:'ok',text:`Acesso validado: organização ${identity.inquilino}; papel ${identity.papel}.`});
    } catch(e) {
      demoAccessToken='';setTokenActive(false);setTokenInput('');
      setNotice({kind:'erro',text:`O acesso não foi validado: ${String((e as Error).message||e)}. Renove o token se necessário.`});
    } finally {setBusy(false);}
  }
  const apiStatusLabel = authMode==='verificando' ? 'Verificando API' : authMode==='offline' ? 'API indisponível' : demoAuth&&!tokenActive ? 'API online · autenticação pendente' : apiHealthy ? 'API central conectada' : 'API conectada · aguardando dados';
  const label:Record<View,string>={visao:'Visão geral',dispositivos:'Dispositivos',perfis:'Perfis',historico:'Histórico',alarmes:'Regras e alarmes',operacao:'Operação',observabilidade:'Observabilidade'};
  const openAlarms=alarms.filter(a=>a.status!=='resolvido');
  const shownAlarms=alarms.filter(a=>alarmFilter==='todos' || (alarmFilter==='abertos' ? a.status!=='resolvido' : a.status===alarmFilter));
  function addRule(e:React.FormEvent){
    e.preventDefault();
    const device=ruleForm.dispositivo||devices[0]?.id;
    if(!device||!ruleForm.nome.trim())return;
    void action(async()=>{
      await submitJson('/api/v1/regras','POST',{
        inquilino:tenant,nome:ruleForm.nome.trim(),dispositivo:device,
        grandeza:ruleForm.grandeza.trim(),unidade:ruleForm.unidade.trim(),
        operador:ruleForm.operador,limite:Number(ruleForm.limite),severidade:ruleForm.severidade
      });
      setRuleForm(old=>({...old,nome:''}));
    },'Regra criada. Ela só será avaliada quando chegar uma nova medição atual.');
  }
  function alarmAction(id:number,verb:'reconhecer'|'resolver'){
    void action(async()=>{
      await submitJson(`/api/v1/alarmes/${id}/${verb}`,'POST',{inquilino:tenant});
    },`Alarme ${verb==='reconhecer'?'reconhecido':'resolvido'} no laboratório.`);
  }


  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">◈</div><div><strong>Integra IoT</strong><small>PLATAFORMA · LAB</small></div></div>
      <div className="nav-label">GERENCIAMENTO</div>
      <nav aria-label="Navegação principal">
        {(['visao','dispositivos','perfis','historico','alarmes','operacao','observabilidade'] as View[]).map((v,i)=><button key={v} className={`nav-link ${view===v?'active':''}`} onClick={()=>setView(v)}><span aria-hidden="true">{['▦','▤','◇','◷','!','◉','≋'][i]}</span>{label[v]}</button>)}
      </nav>
      <div className="sidebar-bottom"><div className="sidebar-status"><span className={`status-dot ${authMode!=='offline'&&authMode!=='verificando'?'online':'offline'}`}/>{apiStatusLabel}</div><small>Interface v0.7.0 · API v0.7.0</small></div>
    </aside>

    <main className="workspace">
      <header className="topbar"><div><span className="eyebrow">UNIEVANGÉLICA / INTERNET DAS COISAS</span><h1>{label[view]}</h1></div>
        <div className="top-actions"><button className="button secondary" disabled={busy} onClick={()=>setRefreshCount(n=>n+1)}>↻ Atualizar</button><a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="button outline">Swagger ↗</a></div>
      </header>
      <div className="lab-warning" role="note"><span aria-hidden="true">⚠</span><div><strong>Ambiente didático local</strong><span>{demoAuth ? 'Modo JWT didático habilitado. Sem OIDC, MFA ou TLS; acesso somente local e sem dados reais.' : 'Modo aberto de laboratório. Sem login ou isolamento de acesso; não exponha à internet nem insira dados reais.'}</span></div></div>
      {demoAuth&&<div className="tenantbar" role="group" aria-label="Token demonstrativo">
        <div><label htmlFor="demo-token">Token de acesso (laboratório)</label><p>Use runtime/token-gestor.txt. Token de 1 hora, somente nesta aba, sem armazenamento permanente.</p></div>
        <form onSubmit={submitToken}>
          <input id="demo-token" type="password" value={tokenInput} onChange={e=>setTokenInput(e.target.value)} placeholder={tokenActive?'Insira um novo token para renovar':'Cole o token JWT local'} autoComplete="off" aria-label="Token de acesso demonstrativo"/>
          <button disabled={busy} type="submit" className="button primary">{tokenActive?'Renovar token':'Validar e entrar'}</button>
          {tokenActive&&<button type="button" className="button secondary" onClick={()=>{demoAccessToken='';setTokenInput('');setTokenActive(false);setDevices([]);setRules([]);setAlarms([]);setReadings([]);setDeviceHealth([]);setCalculatedAt('');setObsSummary(null);setNotice(null);}}>Sair</button>}
        </form>
      </div>}
      <div className="tenantbar"><div><label htmlFor="tenant">Organização (inquilino)</label><p>Filtro didático de dados. Não é autenticação.</p></div><form onSubmit={e=>{e.preventDefault();if(tenantInput.trim()){setProfileDetail(null);setReadings([]);setTenant(tenantInput.trim());}}}><input id="tenant" value={tenantInput} onChange={e=>setTenantInput(e.target.value)} placeholder="coop-cerrado" required/><button className="button primary" type="submit">Aplicar</button></form></div>
      {demoAuth&&!tokenActive&&<div className="lab-warning" role="status"><span aria-hidden="true">🔑</span><div><strong>API ligada; autenticação pendente</strong><span>O painel só carrega dispositivos e alarmes após validar seu token. Não é falha do Docker. Para criar um token novo, execute ./scripts/linux/09-iniciar-protegido.sh na pasta do projeto.</span></div></div>}
      {notice&&<div className={`notice ${notice.kind}`} role="status"><span>{notice.kind==='ok'?'✓':'!'}</span>{notice.text}<button aria-label="Fechar mensagem" onClick={()=>setNotice(null)}>×</button></div>}
      {view==='visao'&&<>
        <div className="hero"><div><div className="kicker">CENTRAL DE MONITORAMENTO</div><h2>Uma visão integrada de dispositivos e leituras.</h2><p>Informações obtidas da API da plataforma, com dados da organização <strong>{tenant}</strong>.</p></div><div className="hero-graphic" aria-hidden="true"><span>◉</span><i/><i/><i/></div></div>
        <div className="metrics">
          <div className="metric"><span>Dispositivos cadastrados</span><strong>{devices.length}</strong><small>Até 500 exibidos nesta consulta</small></div>
          <div className="metric"><span>Perfis configurados</span><strong>{profiles.length}</strong><small>Domínios: {domains.length}</small></div>
          <div className="metric"><span>Leituras suspeitas</span><strong className="orange">{suspicious}</strong><small>No histórico do dispositivo selecionado</small></div>
          <div className="metric"><span>Leituras conformes</span><strong className="green">{conforming}</strong><small>No histórico do dispositivo selecionado</small></div>
        </div>
        <section className="panel compact"><div className="panel-head"><div><h3>Alarmes em aberto</h3><p>{openAlarms.length} ativo(s) ou reconhecido(s) · {rules.length} regras configuradas</p></div><button className="button secondary" onClick={()=>setView('alarmes')}>Gerenciar alarmes →</button></div>{openAlarms.length===0?<p className="subheading">Nenhum alarme em aberto nas últimas consultas.</p>:<div className="stack">{openAlarms.slice(0,3).map(a=><div className="reading-mini" key={a.id}><div><strong>{a.rule_name} · {a.device_id}</strong><small>{a.measurement_name}: {a.last_value} {a.unit}</small></div><span className={`tag ${a.status==='ativo'?'suspeita':'nao_avaliada'}`}>{a.status}</span></div>)}</div>}</section>
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

      {view==='alarmes'&&<>
        <div className="two-columns wide-left">
          <section className="panel"><div className="panel-head"><div><h3>Regras configuradas</h3><p>Condições de limite avaliadas em novas leituras</p></div><span className="count-pill">{rules.length}</span></div>
            <div className="table-wrap"><table><thead><tr><th>Regra / dispositivo</th><th>Condição</th><th>Severidade</th></tr></thead><tbody>{rules.map(r=><tr key={r.id}><td><strong>{r.name}</strong><small className="table-sub">{r.device_id} · {r.measurement_name}</small></td><td>{r.operator==='maior_que'?'>':'<'} {r.threshold} {r.unit}</td><td>{r.severity}</td></tr>)}</tbody></table></div>
            {rules.length===0&&<div className="empty">Ainda não há regras configuradas nesta organização.</div>}
            <p className="footnote">Implementação didática: condição simples de limite e alarme interno; sem comandos físicos, SMS ou webhooks.</p>
          </section>
          <section className="panel"><h3>Criar regra de limite</h3><p className="subheading">Crie uma regra para um dispositivo. Ela não dispara para leituras históricas.</p>
            <form className="field-stack" onSubmit={addRule}>
              <label>Nome da regra<input required maxLength={120} value={ruleForm.nome} onChange={e=>setRuleForm(f=>({...f,nome:e.target.value}))} placeholder="solo-seco"/></label>
              <label>Dispositivo<select required value={devices.some(d=>d.id===ruleForm.dispositivo)?ruleForm.dispositivo:(devices[0]?.id||'')} onChange={e=>setRuleForm(f=>({...f,dispositivo:e.target.value}))}>{devices.length===0?<option value="">Nenhum dispositivo</option>:devices.map(d=><option key={d.id} value={d.id}>{d.id}</option>)}</select></label>
              <label>Grandeza<input required value={ruleForm.grandeza} onChange={e=>setRuleForm(f=>({...f,grandeza:e.target.value}))}/></label>
              <label>Unidade<input required value={ruleForm.unidade} onChange={e=>setRuleForm(f=>({...f,unidade:e.target.value}))}/></label>
              <div className="field-grid"><label>Operador<select value={ruleForm.operador} onChange={e=>setRuleForm(f=>({...f,operador:e.target.value}))}><option value="maior_que">Maior que (&gt;)</option><option value="menor_que">Menor que (&lt;)</option></select></label>
              <label>Limite<input required type="number" step="any" value={ruleForm.limite} onChange={e=>setRuleForm(f=>({...f,limite:e.target.value}))}/></label>
              <label>Severidade<select value={ruleForm.severidade} onChange={e=>setRuleForm(f=>({...f,severidade:e.target.value}))}><option value="baixa">Baixa</option><option value="media">Média</option><option value="alta">Alta</option><option value="critica">Crítica</option></select></label></div>
              <button type="submit" disabled={busy||devices.length===0} className="button primary fill">Salvar regra</button>
            </form>
          </section>
        </div>
        <section className="panel"><div className="panel-head"><div><h3>Alarmes registrados</h3><p>Ciclo de vida: ativo → reconhecido → resolvido</p></div><label className="simple-filter">Filtro <select value={alarmFilter} onChange={e=>setAlarmFilter(e.target.value)}><option value="abertos">Em aberto</option><option value="todos">Todos</option><option value="ativo">Ativos</option><option value="reconhecido">Reconhecidos</option><option value="resolvido">Resolvidos</option></select></label></div>
          <div className="table-wrap"><table><thead><tr><th>Regra / sensor</th><th>Valor</th><th>Estado</th><th>Última medição</th><th>Ação</th></tr></thead><tbody>{shownAlarms.map(a=><tr key={a.id}><td><strong>{a.rule_name}</strong><small className="table-sub">{a.device_id} · {a.severity} · {a.occurrences} ocorrência(s)</small></td><td>{a.last_value} {a.unit}</td><td><span className={`tag ${a.status==='ativo'?'suspeita':a.status==='resolvido'?'conforme':'nao_avaliada'}`}>{a.status}</span></td><td>{dateLabel(a.last_measured_at)}</td><td>{a.status==='ativo'&&<button disabled={busy} className="table-action" onClick={()=>alarmAction(a.id,'reconhecer')}>Reconhecer</button>}{a.status!=='resolvido'&&<button disabled={busy} className="table-action" onClick={()=>alarmAction(a.id,'resolver')}>Resolver</button>}</td></tr>)}</tbody></table></div>
          {shownAlarms.length===0&&<div className="empty">Nenhum alarme corresponde ao filtro.</div>}
          <p className="footnote">Atualize para consultar novos alarmes. Leitura normal mais recente resolve automaticamente um alarme aberto.</p>
        </section>
      </>}

      {view==='operacao'&&<>
        <section className="panel">
          <div className="panel-head"><div><h3>Estado estimado dos dispositivos</h3><p>Comparação entre o horário da última medição e o intervalo esperado no perfil</p></div><button className="button secondary" onClick={()=>setRefreshCount(c=>c+1)} disabled={busy}>↻ Atualizar</button></div>
          <p className="subheading">Referência: {calculatedAt?dateLabel(calculatedAt):'ainda não consultado'}. O sensor é classificado como atrasado após 2× o intervalo de envio. Não é teste real de conexão ou heartbeat.</p>
          <div className="metrics three"><div className="metric"><span>Em dia</span><strong className="green">{deviceHealth.filter(d=>d.estado==='em_dia').length}</strong></div><div className="metric"><span>Atrasados</span><strong className="orange">{deviceHealth.filter(d=>d.estado==='atrasado').length}</strong></div><div className="metric"><span>Sem dados / perfil / relógio</span><strong>{deviceHealth.filter(d=>d.estado!=='em_dia'&&d.estado!=='atrasado').length}</strong></div></div>
          <div className="table-wrap"><table><thead><tr><th>Dispositivo</th><th>Perfil</th><th>Última medição</th><th>Intervalo esperado</th><th>Estado</th></tr></thead><tbody>{deviceHealth.map(d=><tr key={d.id}><td><strong>{d.id}</strong><small className="table-sub">{d.site} · {d.domain}</small></td><td>{d.profile_name||'—'}</td><td>{d.last_measured_at?dateLabel(d.last_measured_at):'Nunca recebeu'}</td><td>{d.expected_interval_seconds===null?'—':`${d.expected_interval_seconds} s`}</td><td><span className={`tag ${d.estado==='em_dia'?'conforme':d.estado==='atrasado'?'suspeita':'nao_avaliada'}`}>{({em_dia:'Em dia',atrasado:'Atrasado',sem_dados:'Sem dados',sem_perfil:'Sem perfil',relogio_inconsistente:'Relógio inconsistente'} as Record<string,string>)[d.estado]}</span></td></tr>)}</tbody></table></div>
          {deviceHealth.length===0&&<div className="empty">Nenhum dispositivo retornado para esta organização.</div>}
          <p className="footnote">Dados atrasados não são tratados como atuais por terem chegado hoje. A classificação é estimada e não aciona alarmes nem muda o banco. O endpoint retorna no máximo 500 dispositivos por consulta.</p>
        </section>
      </>}

      {view==='observabilidade'&&<>
        <section className="panel">
          <div className="panel-head">
            <div><h3>Indicadores históricos da organização</h3><p>Consultados diretamente no PostgreSQL, sem expor métricas de outras organizações</p></div>
            <button className="button secondary" onClick={()=>setRefreshCount(c=>c+1)} disabled={busy}>↻ Atualizar</button>
          </div>
          {!obsSummary?<div className="empty">Aguardando consulta autenticada à API.</div>:<>
            <div className="metrics">
              <div className="metric"><span>Mensagens persistidas</span><strong>{obsSummary.mensagens_persistidas}</strong><small>Exclui retransmissões duplicadas</small></div>
              <div className="metric"><span>Medições conformes</span><strong className="green">{obsSummary.classificacoes.conforme}</strong><small>Classificação dos perfis</small></div>
              <div className="metric"><span>Medições suspeitas</span><strong className="orange">{obsSummary.classificacoes.suspeita}</strong><small>Fora das regras do perfil</small></div>
              <div className="metric"><span>Alarmes em aberto</span><strong>{obsSummary.alarmes_abertos}</strong><small>Ativos ou reconhecidos</small></div>
            </div>
            <div className="stack" style={{marginTop:16}}>
              <div className="reading-mini"><strong>Última recepção registrada</strong><span>{obsSummary.ultima_recepcao?dateLabel(obsSummary.ultima_recepcao):'Nenhuma'}</span></div>
              <div className="reading-mini"><strong>Medições não avaliadas</strong><span>{obsSummary.classificacoes.nao_avaliada}</span></div>
            </div>
            <p className="footnote">{obsSummary.aviso}</p>
          </>}
        </section>
        <section className="panel">
          <h3>Métricas técnicas e logs estruturados</h3>
          <p className="subheading">A API exporta contadores de requisições e ingestão, além de histogramas de latência no formato Prometheus. Os contadores em memória reiniciam quando o processo é reiniciado.</p>
          <p className="footnote">No modo protegido, <code>/metrics</code> é restrito a administradores porque agrega tráfego de toda a instalação. Gestores podem consultar apenas o resumo de sua organização. Os registros JSON ficam nos logs do Docker e incluem um identificador de correlação, sem conteúdo da telemetria ou tokens.</p>
          <p className="footnote">Observabilidade básica de laboratório: ainda não há Prometheus/Grafana, alertas operacionais, retenção de logs, OpenTelemetry ou rastreamento distribuído.</p>
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
      <footer>Plataforma IoT Integrada · Laboratório acadêmico · v0.7.0 · Dados sintéticos</footer>
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
